FROM python:3.12-slim

# install deps and create a non-root user
RUN pip install --no-cache-dir flask==3.0.2 werkzeug==3.0.1 && \
    adduser --disabled-password --gecos '' appuser

WORKDIR /app
COPY app.py .
USER appuser

ENV FLASK_APP=app.py
ENV UPLOAD_DIR=/uploads
EXPOSE 80
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
