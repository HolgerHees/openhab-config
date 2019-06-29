#/bin/sh

mogrify -background "#00000000" -path png/ -format png new/*.svg
