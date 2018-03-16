#!/bin/bash

NAME_ROOT=electrum-ftc
PYTHON_VERSION=3.5.4

# These settings probably don't need any change
export WINEPREFIX=/opt/wine64
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=22
export WINEPATH="c:\\mingw32\\bin"

PYHOME=c:/python$PYTHON_VERSION
PYTHON="wine $PYHOME/python.exe -OO -B"


# Let's begin!
cd `dirname $0`
set -e

mkdir -p tmp
cd tmp

git clone https://github.com/spesmilo/electrum-locale.git

pushd electrum-locale
for i in ./locale/*; do
    dir=$i/LC_MESSAGES
    mkdir -p $dir
    msgfmt --output-file=$dir/electrum.mo $i/electrum.po || true
done
popd

if [ -n "$TRAVIS" ]; then
    ln -s $TRAVIS_BUILD_DIR $WINEPREFIX/drive_c/electrum
fi

pushd $WINEPREFIX/drive_c/electrum
if [ ! -z "$1" ]; then
    git checkout $1
fi

VERSION=`git describe --always --tags --dirty`
echo "Last commit: $VERSION"
find -type f -exec touch -d '2000-11-11T11:11:11+00:00' {} +
find -type d -exec touch -d '2000-11-11T11:11:11+00:00' {} +
popd

cp -r electrum-locale/locale $WINEPREFIX/drive_c/electrum/lib/

# Install frozen dependencies
$PYTHON -m pip install -r ../../deterministic-build/requirements.txt

$PYTHON -m pip install -r ../../deterministic-build/requirements-hw.txt

pushd $WINEPREFIX/drive_c/electrum
# byte-compiling is needed to install neoscrypt properly
PYTHONDONTWRITEBYTECODE="" ${PYTHON/ -B/} setup.py install
popd

cd ..

rm -rf dist/

# build standalone and portable versions
wine "C:/python$PYTHON_VERSION/scripts/pyinstaller.exe" --noconfirm --ascii --name $NAME_ROOT-$VERSION -w deterministic.spec

# set timestamps in dist, in order to make the installer reproducible
pushd dist
find -exec touch -d '2000-11-11T11:11:11+00:00' {} +
popd

# build NSIS installer
# $VERSION could be passed to the electrum.nsi script, but this would require some rewriting in the script itself.
wine "$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe" /DPRODUCT_VERSION=$VERSION electrum.nsi

cd dist
mv electrum-setup.exe $NAME_ROOT-$VERSION-setup.exe
cd ..

echo "Done."
md5sum dist/electrum*exe
