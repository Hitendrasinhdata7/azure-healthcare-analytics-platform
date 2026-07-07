# Placeholder Dockerfile for the sample-service referenced by CI.
# Swap for the real application's build in an actual deployment.
FROM alpine:3.20
RUN adduser -D -u 10001 appuser
USER appuser
COPY --chown=appuser:appuser . /app
WORKDIR /app
EXPOSE 8080
CMD ["echo", "sample-service placeholder"]
