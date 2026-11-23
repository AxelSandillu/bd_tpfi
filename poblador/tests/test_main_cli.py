from main import build_parser


def test_cli_reconoce_argumentos():
    args = build_parser().parse_args([
        "--seed", "123", "--offline", "--salida", "out.sql", "--config", "custom.py"
    ])
    assert args.seed == 123
    assert args.offline is True
    assert args.salida == "out.sql"
    assert args.config == "custom.py"
