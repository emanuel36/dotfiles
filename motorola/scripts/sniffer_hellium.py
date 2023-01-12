#! /usr/bin/python

import re
from pathlib import Path
import sys
import signal
import logging
import subprocess
import time
import argparse
import multiprocessing
from datetime import datetime


# Class to catch the ctrl + c interrupt (sigint)
class InterruptHandler(object):
    def __init__(self, sig=signal.SIGINT):
        self.sig = sig

    def __enter__(self):

        self.interrupted = False
        self.released = False

        self.original_handler = signal.getsignal(self.sig)

        def handler(signum, frame):
            self.release()
            self.interrupted = True

        signal.signal(self.sig, handler)

        return self

    def __exit__(self, type, value, tb):
        self.release()

    def release(self):

        if self.released:
            return False

        signal.signal(self.sig, self.original_handler)

        self.released = True

        return True


def run_adb_cmd(device=None, adb_cmd="shell", error_message=None, raise_exception=True, adb_path=None):
    output = None

    if adb_path is not None:
        run_adb_cmd.adb_path = adb_path

    cmd =  run_adb_cmd.adb_path
    if device:
        cmd += " -s " + device

    cmd += " " + adb_cmd

    logging.debug("Run: %s" % cmd)

    try:
        output = subprocess.check_output(
            cmd, shell=True, stderr=subprocess.STDOUT
        ).decode("utf-8")
    except subprocess.CalledProcessError as e:
        if raise_exception:
            if error_message:
                logging.error(error_message)
            # raise exception only if we need it
            raise e

    return output


def error_exit():
    input("Error encountered... Press enter to abort.")
    sys.exit()


def sync_time(device):
    print("Synchronizing device time with computer time.")

    run_adb_cmd(
        device, "shell date `date +%m%d%H%M%G.%S`", "Could not synchronize the time."
    )


def init_config(device):

    # run adb remount
    # run_adb_cmd(device, "remount", "Could not remount the device.")

    sync_time(device)

    # set con_mode to default 0
    run_adb_cmd(
        device,
        'shell "echo 0 > /sys/module/wlan/parameters/con_mode"',
        "Could not configure con_mode.",
    )

    # enable wlan0
    run_adb_cmd(device, 'shell "ip link set wlan0 up"',
                "Could not configure wlan0.")

    # enable wifi
    wait_for_wlan_up(device)


def scan_ssids(device):
    print("Scanning wifi networks.")
    retry = 5
    retry_delay = 2
    # scan and return all information for available ssids
    while retry >= 0:
        raise_exception = not retry
        scan = run_adb_cmd(device, 'shell "iw dev wlan0 scan"',
                           "Could not scan the ssids.", raise_exception)
        # check if the scan returned is valid
        if type(scan) == str and not re.search("scan aborted!", scan):
            break
        # error if retry timeout. (retry reaches 0 but scan is aborted instead of failing)
        if not retry:
            logging.error(
                "Number of retries reached for scanning the networks.")
            error_exit()

        retry -= 1
        time.sleep(retry_delay)

    # split scan based on "on wlan" that appears on first line of each network scanned
    scan = list(scan.split("on wlan"))
    del scan[0]
    freqs, ssids = [], []

    for x in scan:
        ssid = re.search(r"SSID:.*", x)
        freq = re.search(r"freq:.*", x)
        if ssid is not None and freq is not None:
            ssids.append(ssid.group(0).split(":")[1].strip())
            freqs.append(freq.group(0).split(":")[1].strip())

    return scan, ssids, freqs


def select_input(scan_len, input_name):
    # get and validate user input
    inp = -1
    while not inp in range(0, scan_len):
        inp = int(input(f"Select {input_name}:"))
    return inp


def get_bandwidth(scan, n):
    scan = scan[n]
    # channel width: 1 = 80 MHz, channel width: 0 = 20 or 40 MHz
    # When STA channel width: any, we use 40MHz (channel width: 0)
    bw = re.search(r"\*.channel.width:.1", scan)
    if not bw:
        bw = re.search(r"STA.channel.width:.*",
                       scan).group().split(":")[1].strip()
        bw = 1 if bw == "any" else 0
    else:
        bw = 2

    return bw


def wait_for_wlan_down(device):
    run_adb_cmd(
        device, 'shell "cmd wifi set-wifi-enabled disabled"', "Could not turn off wifi."
    )

    wifioff = None
    while not wifioff:
        wifioff = re.search(
            r"Wifi is disabled",
            run_adb_cmd(device, 'shell "cmd wifi status"',
                        "Could not get wifi status."),
        )


def wait_for_wlan_up(device):
    run_adb_cmd(
        device, 'shell "cmd wifi set-wifi-enabled enabled"', "Could not turn off wifi."
    )

    wifion = None
    while not wifion:
        wifion = re.search(
            r"Wifi is enabled",
            run_adb_cmd(device, 'shell "cmd wifi status"',
                        "Could not get wifi status."),
        )


def configure_sniffer_capture(device, freq, bw):
    print("Configuring sniffer capture.")
    # set con_mode to 4, to enter sniffer mode
    run_adb_cmd(
        device,
        'shell "echo 4 > /sys/module/wlan/parameters/con_mode"',
        "Could not set con_mode to 4.",
    )

    wait_for_wlan_down(device)
    restart_wlan(device)

    command = f'shell "iwpriv wlan0 setMonChan {freq} {bw}"'

    run_adb_cmd(
        device,
        command,
        f"Could not configure the sniffer. freq={freq} bw={bw}",
    )


def run_sniffer_capture(device):
    print("Starting the sniffer process.")
    try:
        run_adb_cmd(
            device,
            'shell "tcpdump -i wlan0 -w /sdcard/capture.pcap -C 500 -W 20"',
            "Could not RUN the sniffer process.",
        )

    # Sniffer process will stop when SIGINT (ctrl + c) is used
    except KeyboardInterrupt:
        pass


def collect_logs(device):
    file_name = datetime.now().strftime("%m-%d-%y_%H.%M.%S_sniffer.tar.gz")
    print("\nCollecting logs.")

    # Compress the sniffer logs
    run_adb_cmd(
        device,
        f'shell "cd sdcard && tar cvzf {file_name} capture*"',
        "Could not compress the sniffer captured.",
    )

    # Pull the compressed capture
    run_adb_cmd(
        device,
        f"pull sdcard/{file_name}",
        "Could not pull the compressed sniffer captured.",
    )

    current_path = str(Path.cwd())
    print(f"Logs saved at: {current_path}/{file_name}")


def restore_configs(device):
    # Restore device connection mode, or else device won't connect to wifi
    run_adb_cmd(
        device,
        'shell "echo 0 > /sys/module/wlan/parameters/con_mode"',
        "Could not reconfigure con_mode.",
    )


def restart_wlan(device):
    run_adb_cmd(device, 'shell "ip link set wlan0 down"',
                "Could not turn off wlan0.")

    run_adb_cmd(device, 'shell "ip link set wlan0 up"',
                "Could not turn on wlan0.")


def get_device_list():
    device_list = [y.split()[0] for y in run_adb_cmd(
        None, 'devices', 'Could not get device list.').splitlines() if y]
    return device_list[1:]


def select_device():
    device_list = get_device_list()
    num_devices = len(device_list)

    # No devices or only one device found
    if num_devices <= 1:
        wait_for_device()
        return get_device_list()[0]

    print("\nList of available devices:\n")
    for i in range(0, num_devices):
        print(f"{i}: {device_list[i]}")
    print("\n")

    inp = select_input(num_devices, "device")

    return device_list[inp]


def wait_for_device():
    logging.debug("Waiting for device")
    run_adb_cmd(None, "wait-for-device", "Something wrong with ADB.")
    logging.debug("Device found")


def adb_root(device):
    run_adb_cmd(device, "root", "Can't run adb on root")


def select_ssid(ssids, freqs):
    print("\nList of available ssids:\n")

    for i in range(len(ssids)):
        ssids[i] = ssids[i] if ssids[i] else "hidden"
        print(f"{i}: {ssids[i]} - {freqs[i]}MHz")

    print("\n")

    return select_input(len(ssids), "ssid")


def run_sniffer_process_and_wait_for_sigint(device):
    p = multiprocessing.Process(
        target=run_sniffer_capture,
        args=(
            device,
        ),
    )
    # Start sniffer process
    p.start()
    # Wait 2 seconds to print message, or else the it won't print in the correct order
    time.sleep(2)
    print("Sniffer is running. To finish, press ctrl + c to terminate sniffer process.")
    with InterruptHandler() as h:
        while True:
            if h.interrupted:
                break
    p.terminate()
    # wait for the sniffer process to terminate
    while p.is_alive():
        time.sleep(0.1)
    p.close()


def check_adb_executable():
    try:
        run_adb_cmd(None, "--version", raise_exception=False, adb_path=str(Path(__file__).parent/"adb"))
        logging.debug("Using adb on script folder.")
    except subprocess.CalledProcessError as e:
        # Try adb installed on path variable
        run_adb_cmd(None, "--version", "Could not find adb.", adb_path="adb")
        logging.debug("Using adb installed on path variable.")


def capture_sniffer(args):
    device = args.device
    bw = args.bandwidth
    freq = args.frequency

    if not device:
        device = select_device()

    adb_root(device)
    init_config(device)

    if not freq:
        scan, ssids, freqs = scan_ssids(device)
        inp = select_ssid(ssids, freqs)
        freq = int(freqs[inp])

        if not bw:
            bw = get_bandwidth(scan, inp)

    configure_sniffer_capture(device, freq, bw)
    run_sniffer_process_and_wait_for_sigint(device)
    collect_logs(device)
    restore_configs(device)
    input("Sniffer captured. Press enter to exit.")


if __name__ == "__main__":
    # On Windows calling this function is necessary for
    # pyinstaller to work properly with multiprocessing
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Collect sniffer logs.")

    # Commands to parse
    parser.add_argument(
        "-v", "--verbose", help="Show the adb commands used", action="store_true"
    )

    parser.add_argument(
        "-f", "--frequency", type=str, help="Specify the frequency. If not specified, the script " +
        "will show the scanned network frequencies. Need to specify the bandwidth with --bandwidth.",
    )

    parser.add_argument(
        "-b", "--bandwidth", help="Specify the bandwidth. If not specified, the script " +
        "will try to find the bandwidth on scan results. 0 - 20Mhz, 1 - 40MHz, 2 - 80MHz, 3 - 160MHz",
        choices=['0', '1', '2', '3'],
    )

    parser.add_argument("-d", "--device", type=str,
                        help="Specify the device to use")

    # Object containing the arguments, we can retrieve the arguments calling args.<command>
    # Command is --<command> or -<command>
    args = parser.parse_args()

    if  args.frequency is not None and args.bandwidth is None:
        parser.error("--frequency requires --bandwidth.")

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Check python version. This is necessary for using Process.close(), which was
    # added at python version 3.7. Tested with pyinstaller, no problems checking it.
    if int(sys.version_info[0]) < 3 or int(sys.version_info[1]) < 7:
        logging.error("Python version must be >= 3.7")
        error_exit()

    check_adb_executable()

    capture_sniffer(args)
