# Imagen del frontend: se compila con Node y lo sirve Nginx.
FROM node:24-alpine AS compilar
WORKDIR /app
COPY package.json package-lock.json ./
# `npm install` y no `npm ci`: el package-lock generado en Windows no trae algunas
# dependencias opcionales de Linux y `npm ci` lo rechaza por desincronizado.
RUN npm install --no-audit --no-fund
COPY . .
# La URL del backend queda fija al compilar: la usa el navegador, no el contenedor.
# Vacía = el mismo equipo que sirve la página, puerto 8000 (sirve también desde un
# celular en la misma Wi-Fi).
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=compilar /app/dist /usr/share/nginx/html
EXPOSE 80
