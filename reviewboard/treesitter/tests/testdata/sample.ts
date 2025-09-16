import { EventEmitter } from 'events';

// Type definitions
interface User {
  readonly id: number;
  name: string;
  email?: string;
  roles: Role[];
}

type Role = 'admin' | 'user' | 'moderator';

interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
}

// Generic class
class DataStore<T extends { id: number }> extends EventEmitter {
  private items: Map<number, T> = new Map();

  constructor(private readonly storeName: string) {
    super();
  }

  add(item: T): void {
    this.items.set(item.id, item);
    this.emit('itemAdded', item);
  }

  get(id: number): T | undefined {
    return this.items.get(id);
  }

  getAll(): T[] {
    return Array.from(this.items.values());
  }

  update(id: number, updates: Partial<T>): boolean {
    const item = this.items.get(id);
    if (!item) return false;

    const updatedItem = { ...item, ...updates };
    this.items.set(id, updatedItem);
    this.emit('itemUpdated', updatedItem);
    return true;
  }

  delete(id: number): boolean {
    const deleted = this.items.delete(id);
    if (deleted) {
      this.emit('itemDeleted', id);
    }
    return deleted;
  }

  count(): number {
    return this.items.size;
  }
}

// User service with async operations
class UserService {
  private userStore = new DataStore<User>('users');
  private static instance: UserService;

  private constructor() {
    this.userStore.on('itemAdded', (user) => {
      console.log(`User added: ${user.name}`);
    });
  }

  static getInstance(): UserService {
    if (!UserService.instance) {
      UserService.instance = new UserService();
    }
    return UserService.instance;
  }

  async createUser(name: string, email?: string, roles: Role[] = ['user']): Promise<ApiResponse<User>> {
    try {
      const user: User = {
        id: Date.now(), // Simple ID generation
        name,
        email,
        roles,
      };

      // Simulate async validation
      await this.validateUser(user);

      this.userStore.add(user);

      return {
        data: user,
        status: 'success',
        message: 'User created successfully',
      };
    } catch (error) {
      return {
        data: {} as User,
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  private async validateUser(user: User): Promise<void> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (!user.name.trim()) {
          reject(new Error('Name is required'));
        } else if (user.email && !this.isValidEmail(user.email)) {
          reject(new Error('Invalid email format'));
        } else {
          resolve();
        }
      }, 100);
    });
  }

  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  getUsersByRole(role: Role): User[] {
    return this.userStore.getAll().filter(user => user.roles.includes(role));
  }

  // Arrow function with destructuring
  updateUserRoles = (userId: number, newRoles: Role[]): boolean => {
    return this.userStore.update(userId, { roles: newRoles });
  };
}

// Utility functions with various TypeScript features
namespace Utils {
  export function debounce<T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {
    let timeoutId: NodeJS.Timeout;

    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  }

  export function groupBy<T, K extends string | number>(
    array: T[],
    keyFn: (item: T) => K
  ): Record<K, T[]> {
    return array.reduce((groups, item) => {
      const key = keyFn(item);
      (groups[key] = groups[key] || []).push(item);
      return groups;
    }, {} as Record<K, T[]>);
  }
}

// Usage example
async function main(): Promise<void> {
  const userService = UserService.getInstance();

  // Create some users
  const users = await Promise.all([
    userService.createUser('Alice Johnson', 'alice@example.com', ['admin', 'user']),
    userService.createUser('Bob Smith', 'bob@test.com'),
    userService.createUser('Carol Davis', undefined, ['moderator']),
  ]);

  // Filter and log successful creations
  const successfulUsers = users
    .filter((response): response is ApiResponse<User> & { status: 'success' } => 
      response.status === 'success')
    .map(response => response.data);

  console.log('Created users:', successfulUsers);

  // Group users by role
  const allUsers = successfulUsers;
  const usersByRole = Utils.groupBy(allUsers, user => user.roles[0]);
  console.log('Users by primary role:', usersByRole);

  // Debounced function example
  const debouncedLog = Utils.debounce((message: string) => {
    console.log(`Debounced: ${message}`);
  }, 300);

  // This will only log once after 300ms
  debouncedLog('Hello');
  debouncedLog('World');
  debouncedLog('!');
}

// Conditional execution
if (require.main === module) {
  main().catch(console.error);
}

export { UserService, User, Role, ApiResponse };
