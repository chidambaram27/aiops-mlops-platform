# kagent/model_tool/Dockerfile
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY kagent_model_tool.py .

# Set FastMCP to use HTTP transport
ENV FASTMCP_TRANSPORT=http
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8080

# Expose HTTP port for MCP server
EXPOSE 8080

# Run the FastMCP server
CMD ["python", "kagent_model_tool.py"]