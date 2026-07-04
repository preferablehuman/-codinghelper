FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install --omit=dev

EXPOSE 8200

CMD ["node", "server.js"]
