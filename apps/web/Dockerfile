FROM node:24-slim AS build

WORKDIR /web
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json ./
RUN npm ci --workspaces=false

COPY index.html postcss.config.js tailwind.config.ts tsconfig.json tsconfig.node.json vite.config.ts vitest.config.ts ./
COPY src ./src

RUN npm run build --workspaces=false

FROM nginx:1.29-alpine

COPY --from=build /web/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
