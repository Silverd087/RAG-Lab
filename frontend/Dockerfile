FROM node:20 AS builder

WORKDIR /usr/src/app

RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/root/.npm \
    npm ci

COPY . .

RUN npm run build

FROM nginx:alpine AS runtime

WORKDIR /app

COPY --from=builder /usr/src/app/dist ./

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80


