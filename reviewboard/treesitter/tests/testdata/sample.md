# TreeSitter Markdown Test

This is a **sample Markdown file** for testing TreeSitter highlighting with code block injections.

## Python Example

Here's a simple Python function:

```python
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)

# Test the function
for i in range(10):
    print(f"fibonacci({i}) = {fibonacci(i)}")
```

## JavaScript Example

And here's some JavaScript code:

```javascript
class DataProcessor {
    constructor(data = []) {
        this.data = data;
        this.processed = false;
    }

    async process() {
        try {
            const results = await Promise.all(
                this.data.map(async (item) => {
                    return await this.processItem(item);
                })
            );

            this.processed = true;
            return results;
        } catch (error) {
            console.error('Processing failed:', error);
            throw error;
        }
    }

    async processItem(item) {
        // Simulate async processing
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(item.toString().toUpperCase());
            }, 100);
        });
    }
}
```

## Shell Script Example

Here's a bash script:

```bash
#!/bin/bash

# Function to check if a directory exists
check_directory() {
    local dir_path="$1"

    if [ -d "$dir_path" ]; then
        echo "Directory '$dir_path' exists"
        return 0
    else
        echo "Directory '$dir_path' does not exist"
        return 1
    fi
}

# Main script
PROJECT_DIR="/home/user/projects"
BACKUP_DIR="/backup"

echo "Starting backup process..."

if check_directory "$PROJECT_DIR"; then
    echo "Creating backup..."
    tar -czf "${BACKUP_DIR}/backup_$(date +%Y%m%d_%H%M%S).tar.gz" "$PROJECT_DIR"
    echo "Backup completed successfully!"
else
    echo "Source directory not found. Backup aborted."
    exit 1
fi
```

## SQL Example

Some SQL queries:

```sql
-- Create a table for users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Insert sample data
INSERT INTO users (username, email) VALUES 
    ('john_doe', 'john@example.com'),
    ('jane_smith', 'jane@example.com'),
    ('bob_wilson', 'bob@example.com');

-- Query with joins and aggregations
SELECT 
    u.username,
    u.email,
    COUNT(p.id) as post_count,
    MAX(p.created_at) as last_post_date
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
WHERE u.is_active = true
GROUP BY u.id, u.username, u.email
HAVING COUNT(p.id) > 0
ORDER BY post_count DESC, u.username ASC;
```

## JSON Example

Configuration file:

```json
{
  "app": {
    "name": "TreeSitter Test App",
    "version": "1.0.0",
    "debug": false
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "testdb",
    "credentials": {
      "username": "testuser",
      "password": "secret123"
    }
  },
  "features": {
    "authentication": true,
    "caching": true,
    "logging": {
      "level": "info",
      "file": "/var/log/app.log"
    }
  },
  "allowed_hosts": [
    "localhost",
    "127.0.0.1",
    "example.com"
  ]
}
```

## Conclusion

This document demonstrates various programming languages embedded in Markdown using fenced code blocks. TreeSitter should be able to highlight both the Markdown syntax and the injected code within each block.

### Features tested:
- **Markdown** basic syntax (headers, bold, lists)
- **Python** code highlighting
- **JavaScript** with classes and async/await
- **Bash** shell scripting
- **SQL** queries with comments
- **JSON** configuration

Each code block should maintain proper syntax highlighting for its respective language while being embedded within the Markdown document structure.
