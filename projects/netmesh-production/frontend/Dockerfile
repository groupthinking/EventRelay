# Build stage
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Accept build arguments for React Environment Variables
ARG REACT_APP_API_URL
ARG REACT_APP_WS_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_WS_URL=$REACT_APP_WS_URL
ENV NODE_OPTIONS="--max-old-space-size=16384"
ENV DISABLE_ESLINT_PLUGIN=true
ENV GENERATE_SOURCEMAP=false

RUN echo "Listing src/lib:" && ls -F src/lib
RUN echo "Listing src/components/dashboard:" && ls -F src/components/dashboard

RUN npm run build

# Production stage
FROM node:20-slim
WORKDIR /app
COPY --from=build /app/build ./build
COPY package*.json ./
RUN npm install --omit=dev && npm install -g serve
ENV NODE_ENV=production
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
