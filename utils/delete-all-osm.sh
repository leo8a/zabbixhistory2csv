#!/bin/bash

for ns in `osm ns-list | awk '{print $2}'`; do
  echo
  echo 'Removing the NS:' $ns

  osm ns-delete $ns

done

for vim in `osm vim-list | awk '{print $2}'`; do
  echo
  echo 'Removing the VIM:' $vim

  osm vim-delete $vim

done
