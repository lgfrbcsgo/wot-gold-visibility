#!/bin/bash
version=1.0.0.3
particles_pkg=/mnt/c/Games/World_of_Tanks/res/packages/particles.pkg
packages=( blue lightblue cyan green limegreen purple pink red orange yellow )
colors=( 0056FF 0095FF 00FFFF 00F000 6BFF00 C000FF FF00F4 FF0000 FF9000 FFF700 )
for ((i=0; i<${#packages[@]}; i++)); do 
	python2 build.py $particles_pkg package $version "goldvisibility_${packages[$i]}.zip" "${colors[$i]}"
done
