{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = [
    pkgs.python38
    pkgs.python38Packages.pytest
    pkgs.python38Packages.pytest-cov
    pkgs.python38Packages.pytest-html
  ];

  shellHook = ''
    alias test='./runtest'
  '';
}
