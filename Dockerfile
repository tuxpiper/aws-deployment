FROM alpine:latest
MAINTAINER maintainers@codeship.com

RUN apk --update add \
    bash \
    jq \
    py-pip \
    python \
    curl \
    zip && \
  pip install awscli j2cli && \
  rm var/cache/apk/*

COPY scripts/ /usr/bin/
