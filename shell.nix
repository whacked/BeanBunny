{ pkgs ? import <nixpkgs> {} }:
let 
  python38Packages_flatten_dict = pkgs.python38.pkgs.buildPythonPackage rec {
    pname = "flatten-dict";
    version = "0.4.2";
    src = pkgs.python38.pkgs.fetchPypi {
      inherit pname version;
      sha256 = "0xihnim27ympw7dq17gdknkmzsqb54qry3vawhdbh1gqwsv9csjh";
    };

    propagatedBuildInputs = [
      pkgs.python38Packages.six
    ];
  };
in pkgs.mkShell {
  buildInputs = [
    pkgs.python38
    pkgs.python38Packages.ipython
    pkgs.python38Packages.pytest
    pkgs.python38Packages.pytest-cov
    pkgs.python38Packages.pytest-html
    pkgs.python38Packages.pytest-watch
    python38Packages_flatten_dict
  ];

  shellHook = ''
    alias test='./runtest'
  '';
}
