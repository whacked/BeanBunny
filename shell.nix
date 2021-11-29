{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = [
    pkgs.python38
    pkgs.python38Packages.ipython
    pkgs.python38Packages.pytest
    pkgs.python38Packages.pytest-cov
    pkgs.python38Packages.pytest-html
    pkgs.python38Packages.pytest-watch
    pkgs.python38Packages.toolz
  ];

  shellHook = ''
    alias test='./runtest'
  '';
}
