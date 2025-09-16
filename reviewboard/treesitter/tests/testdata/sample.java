package com.example.demo;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;
import java.util.stream.Collectors;
import java.time.LocalDateTime;

/**
 * Example Java class demonstrating various language features
 * @author ReviewBoard Team
 * @version 1.0
 */
public class UserManager {

    // Constants
    private static final int MAX_USERS = 1000;
    private static final String DEFAULT_ROLE = "USER";

    // Instance variables
    private final Map<Long, User> users;
    private final Set<String> validRoles;
    private long nextId;

    // Static initializer
    static {
        System.out.println("UserManager class loaded");
    }

    // Constructor
    public UserManager() {
        this.users = new ConcurrentHashMap<>();
        this.validRoles = Set.of("USER", "ADMIN", "MODERATOR");
        this.nextId = 1L;
    }

    /**
     * Creates a new user with validation
     * @param name The user's name
     * @param email The user's email
     * @param role The user's role
     * @return The created user
     * @throws IllegalArgumentException if validation fails
     */
    public User createUser(String name, String email, String role)
            throws IllegalArgumentException {

        // Input validation
        Objects.requireNonNull(name, "Name cannot be null");
        Objects.requireNonNull(email, "Email cannot be null");

        if (name.trim().isEmpty()) {
            throw new IllegalArgumentException("Name cannot be empty");
        }

        if (!isValidEmail(email)) {
            throw new IllegalArgumentException("Invalid email format");
        }

        if (role == null) {
            role = DEFAULT_ROLE;
        }

        if (!validRoles.contains(role.toUpperCase())) {
            throw new IllegalArgumentException("Invalid role: " + role);
        }

        // Check user limit
        if (users.size() >= MAX_USERS) {
            throw new IllegalStateException("Maximum user limit reached");
        }

        // Create and store user
        User user = new User(nextId++, name.trim(), email.toLowerCase(),
                           role.toUpperCase(), LocalDateTime.now());
        users.put(user.getId(), user);

        return user;
    }

    /**
     * Finds users matching the given predicate
     */
    public List<User> findUsers(Predicate<User> predicate) {
        return users.values()
                   .stream()
                   .filter(predicate)
                   .sorted(Comparator.comparing(User::getName))
                   .collect(Collectors.toList());
    }

    // Method overloading
    public Optional<User> getUser(Long id) {
        return Optional.ofNullable(users.get(id));
    }

    public Optional<User> getUser(String email) {
        return users.values()
                   .stream()
                   .filter(user -> user.getEmail().equals(email.toLowerCase()))
                   .findFirst();
    }

    /**
     * Updates user information asynchronously
     */
    public CompletableFuture<Boolean> updateUserAsync(Long id, String newName, String newEmail) {
        return CompletableFuture.supplyAsync(() -> {
            User user = users.get(id);
            if (user == null) {
                return false;
            }

            // Create updated user (immutable pattern)
            User updatedUser = new User(
                user.getId(),
                newName != null ? newName.trim() : user.getName(),
                newEmail != null ? newEmail.toLowerCase() : user.getEmail(),
                user.getRole(),
                user.getCreatedAt()
            );

            users.put(id, updatedUser);
            return true;
        });
    }

    // Anonymous class example
    public void processUsers() {
        Runnable processor = new Runnable() {
            @Override
            public void run() {
                System.out.println("Processing " + users.size() + " users");
                users.values().forEach(user -> {
                    System.out.printf("User: %s (%s) - %s%n",
                                    user.getName(), user.getEmail(), user.getRole());
                });
            }
        };

        processor.run();
    }

    // Lambda expressions and method references
    public Map<String, Long> getRoleStatistics() {
        return users.values()
                   .stream()
                   .collect(Collectors.groupingBy(
                       User::getRole,
                       Collectors.counting()
                   ));
    }

    private boolean isValidEmail(String email) {
        return email != null &&
               email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$");
    }

    // Nested static class
    public static class User {
        private final Long id;
        private final String name;
        private final String email;
        private final String role;
        private final LocalDateTime createdAt;

        public User(Long id, String name, String email, String role, LocalDateTime createdAt) {
            this.id = id;
            this.name = name;
            this.email = email;
            this.role = role;
            this.createdAt = createdAt;
        }

        // Getters
        public Long getId() { return id; }
        public String getName() { return name; }
        public String getEmail() { return email; }
        public String getRole() { return role; }
        public LocalDateTime getCreatedAt() { return createdAt; }

        @Override
        public boolean equals(Object obj) {
            if (this == obj) return true;
            if (obj == null || getClass() != obj.getClass()) return false;
            User user = (User) obj;
            return Objects.equals(id, user.id);
        }

        @Override
        public int hashCode() {
            return Objects.hash(id);
        }

        @Override
        public String toString() {
            return String.format("User{id=%d, name='%s', email='%s', role='%s'}",
                               id, name, email, role);
        }
    }

    // Enum example
    public enum UserStatus {
        ACTIVE("Active"),
        INACTIVE("Inactive"),
        SUSPENDED("Suspended"),
        PENDING("Pending Verification");

        private final String description;

        UserStatus(String description) {
            this.description = description;
        }

        public String getDescription() {
            return description;
        }
    }

    // Main method for testing
    public static void main(String[] args) {
        UserManager manager = new UserManager();

        try {
            // Create some test users
            User alice = manager.createUser("Alice Johnson", "alice@example.com", "ADMIN");
            User bob = manager.createUser("Bob Smith", "bob@test.com", null);
            User carol = manager.createUser("Carol Davis", "carol@company.org", "MODERATOR");

            System.out.println("Created users:");
            manager.processUsers();

            // Find admin users
            List<User> admins = manager.findUsers(user -> "ADMIN".equals(user.getRole()));
            System.out.println("\nAdmin users: " + admins);

            // Get role statistics
            Map<String, Long> stats = manager.getRoleStatistics();
            System.out.println("\nRole statistics: " + stats);

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
}
