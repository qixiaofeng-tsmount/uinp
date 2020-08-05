list() { ## Used to list all commands available in .bash_profile.
  local sps="        "
  while read line; do
    if [[ $line =~ ^[a-z0-9_\-]+\(\)[[:blank:]]'{'[[:blank:]]'##' ]] ; then
      local name=`expr "$line" : '\([a-z0-9_\-]\{1,32\}()[[:blank:]]{[[:blank:]]##\)'`
      echo `expr "$name" : '\([a-z0-9_\-]\{1,32\}\)'`
      echo "${line/$name/$sps}"
    elif [[ $line =~ ^'##' ]] ; then
      echo "${line/'##'/$sps}"
    fi
  done < ~/Documents/git-repos/uinp/configs/shortcuts.sh
}

svn_mkdir() { ## Make directory on gsegment svn trunk.
  svn mkdir "http://earth.bao.ac.cn/svn/gsegment/trunk/$1" -m "Make $1"
}

svn_co() { ## Check out from gsegment svn trunk.
  svn co "http://earth.bao.ac.cn/svn/gsegment/trunk/$1"
}

qxf-done() { ## Notify a task is done.
  notify-send "Work done notification" "======= =======\nOne task is done.\n======= =======" -t 5000 -u normal
}

gst() { ## Connect me to gsegment server.
  ssh -o ServerAliveInterval=60 qixiaofeng@112.126.73.197
}

d() { ## Decrypt.
  gpg -o "${1/.gpg/.txt}" -d "$1"
}

c() { ## Encrypt.
  gpg -o "${1/.txt/.gpg}" -c "$1"
}

cut_video() { ## Cut video with(time in seconds): cut_video <file> <start_time> <end_time>
  ffmpeg -ss "${2}" -to "${3}" -i "${1}" -vcodec copy -acodec aac -scodec copy "cut_${1}"
  echo "Output to: cut_${1}"
}

# iphone7 1334x750
t1_mp4() { ## Convert to mp4 with bitrate 1024k.
  ffmpeg -i $1 -s 667x375 -vcodec mpeg4 -b:v 1024k -acodec aac -scodec copy "$2.mp4"
}

t2_mp4() { ## Convert to mp4 with bitrate 2048k.
  ffmpeg -i $1 -s 667x375 -vcodec mpeg4 -b:v 2048k -acodec aac -scodec copy "$2.mp4"
}

uinp_up() { ## Only used under windows.
  local curr=`pwd`
  local bpFile="$curr/bash_profile.sh"
  if [ ! -f $bpFile ]; then
    echo "Must execute this under uinp project root."
    return $E_CONFFILE
  fi
  cd ~
  ln -fs $bpFile .bash_profile
  cd $curr
  echo ".bash_profile updated. Restart bash to take effect."
}

wx_rm() { ## Used to remove a page from WeiXin project.
  svn rm --force "$1.js" "$1.json" "$1.wxml" "$1.wxss"
}

git_link() { ## Used to link local with remote repo.
  git remote add origin $1
  git plom --allow-unrelated-histories
}

git_ps() { ## Used to push current branch.
  local branch=`git name-rev --name-only HEAD`
  echo "git push origin ${branch}"
  git push origin ${branch}
}

git_pl() { ## Used to pull current branch.
  local branch=`git name-rev --name-only HEAD`
  echo "git pull origin ${branch}"
  git pull origin ${branch}
}

git_bc() { ## Update branch information for clearing.
  git fetch --prune --all
}

git_up() { ## Used to update the git remote url.
  for url in `git remote -v`; do
    if [ 'git@github.com' == ${url:0:14} ]; then
      git remote set-url origin ${url/qixiaofeng-tsmount/qixiaofeng-gst}
      git remote -v
      return
    fi
  done
}

setup_git() { ## Used to set my email and name for git.
  git config --global user.email "qi_xiaofeng@foxmail.com"
  git config --global user.name "XiaofengQi"
}

enhance_git() { ## Used to set several convenient alias for git.
  git config --global alias.b "branch"
  git config --global alias.st "status"
  git config --global alias.ci "commit -m"
  git config --global alias.co "checkout"
  git config --global alias.plom "pull origin master"
  git config --global alias.psom "push origin master"
}

breakpoint() { ## Used to prompt work progress.
## 1. Record
##    # Collect meta information:
##      * category
##      * trait
##      * pwd
##    # Write information to home directory.
## 2. List
##    # Read records
##    # List records
  echo 'TODO: Implement'
}

gc-make() { ## The make command for gomoku-c.
  pushd cmake-build-release
  make -j4 && ./unit_test
  popd
}

gc-run() { ## The entry shortcut for gomoku-c.
  cd ~/Documents/git-repos/uinp/clanguages/gomoku-c
  cmake-build-release/start_gomoku
}
