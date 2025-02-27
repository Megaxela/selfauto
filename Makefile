build-package:
	python -m pip install --upgrade build
	python -m build

install-package: build-package
	python -m pip install dist/*.tar.gz
