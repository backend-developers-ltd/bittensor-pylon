FROM golang:1.23-alpine

RUN apk add --no-cache git && \
    go install -a github.com/jsonnet-bundler/jsonnet-bundler/cmd/jb@latest && \
    go install github.com/google/go-jsonnet/cmd/jsonnet@latest && \
    mv /go/bin/* /usr/local/bin/ && \
    rm -rf /go

WORKDIR /work
