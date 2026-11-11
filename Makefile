.PHONY: build test verify fetch-whisper fetch-llm finetune doctor fixtures desktop-shortcut remove-desktop-shortcut

build:
	go build -o vox ./cmd/vox

test:
	go test -race ./...
	python3 -m unittest discover -s scripts -p 'test_*.py'

verify: test
	go vet ./...
	bash -n scripts/*.sh
	python3 -m compileall -q scripts

fetch-whisper:
	./scripts/fetch-whisper.sh

fetch-llm:
	./scripts/fetch-llm.sh

finetune:
	./scripts/finetune/run.sh

doctor: build
	./vox doctor

desktop-shortcut: build
	./scripts/install-desktop-shortcut.py

remove-desktop-shortcut:
	./scripts/install-desktop-shortcut.py --remove

fixtures:
	go run scripts/generate-fixtures.go
