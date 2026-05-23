import warnings


warnings.filterwarnings("ignore", category=ResourceWarning, message=r"unclosed <ssl\.SSLSocket.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"ssl\.SSLContext\(\) without protocol argument is deprecated\.")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"ssl\.PROTOCOL_TLS is deprecated")
