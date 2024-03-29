"Plugins
if empty(glob('~/.vim/autoload/plug.vim'))
  silent !curl -fLo ~/.vim/autoload/plug.vim --create-dirs
    \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  autocmd VimEnter * PlugInstall --sync | source $MYVIMRC
endif

" Specify a directory for plugins
" - For Neovim: stdpath('data') . '/plugged'
" - Avoid using standard Vim directory names like 'plugin'
call plug#begin('~/.vim/plugged')

"airline
Plug 'https://github.com/vim-airline/vim-airline'
Plug 'https://github.com/vim-airline/vim-airline-themes'
set ttimeoutlen=50
let g:airline#extensions#hunks#enabled=0
let g:airline#extensions#branch#enabled=1
let g:airline_theme='jellybeans'

"gitgutter
Plug 'https://github.com/airblade/vim-gitgutter'
set updatetime=250
let g:gitgutter_max_signs = 500
highlight GitGutterAdd ctermfg=2
highlight GitGutterChange ctermfg=3
highlight GitGutterDelete ctermfg=1
highlight GitGutterChangeDelete ctermfg=4
highlight! link SignColumn LineNr

"rainbow"
Plug 'https://github.com/frazrepo/vim-rainbow'
let g:rainbow_active = 1

"no tab
Plug 'https://github.com/ntpeters/vim-better-whitespace'

"theme
Plug 'rafalbromirski/vim-aurora'

" Initialize plugin system
call plug#end()

" Settings
set termguicolors
set background=dark
set number
set hlsearch
set incsearch
set ignorecase
set redrawtime=10000
set backspace=indent,eol,start
set expandtab
colorscheme aurora

"Start from last line
if has("autocmd")
  au BufReadPost * if line("'\"") > 0 && line("'\"") <= line("$") | exe "normal! g`\"" | endif
endif

"Commit message limiter
augroup gitsetup
        autocmd!
        autocmd FileType gitcommit
                \  hi def link gitcommitOverflow Error
                \| autocmd CursorMoved,CursorMovedI *
                        \  let &l:textwidth = line('.') == 1 ? 50 : 72
augroup end
