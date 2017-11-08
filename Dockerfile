FROM alpine:latest

LABEL maintainer "Opsani <support@opsani.com>"

WORKDIR /

RUN set -x && \
    apk update && \
    apk upgrade && \
    apk add --update --no-cache \
        python \
        py-simplejson && \
    python -m ensurepip && \
    pip install --upgrade pip && \
    pip install boto3 && \
    pip install web.py && \
    rm -f /usr/lib/python*/distutils/command/wininst*.exe && \
    rm -r /usr/lib/python*/ensurepip && \
    rm -rf /var/cache/apk/* && \
    rm -f /usr/lib/libncursesw.so.6* && \
    rm -f /usr/lib/libsqlite3.so.0*

COPY ./*.py /

# EXPOSE 8000

ENTRYPOINT [ "python", "/ec2-ddsrv.py", "0.0.0.0:8000" ]
