.PHONY: build serve

build:
	bun run build

serve:
	python -mhttp.server
