FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++ wget curl unzip gnupg libgconf-2-4 libx11-6 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libgtk-3-0 libasound2 libxshmfence1 libnss3 libxss1 fonts-liberation libappindicator1 xdg-utils && rm -rf /var/lib/apt/lists/*
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt-get update && apt-get install -y /tmp/chrome.deb && rm /tmp/chrome.deb && rm -rf /var/lib/apt/lists/*
RUN wget -q -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/126.0.6478.61/linux64/chromedriver-linux64.zip && unzip /tmp/chromedriver.zip -d /usr/local/bin/ && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64 && chmod +x /usr/local/bin/chromedriver
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV DISPLAY=:99
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]
