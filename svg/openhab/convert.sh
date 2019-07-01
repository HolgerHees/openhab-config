#/bin/sh

rm png/*.png
rm ../../conf/icons/classic/*.png

mogrify -background "#00000000" -path png/ -format png new/*.svg

cp png/*.png ../../conf/icons/classic/

