#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Global constant
const int MAX_SIZE = 100;

/* Multi-line comment
   demonstrating C syntax */
typedef struct {
    int id;
    char *name;
    float value;
} Record;

// Function prototypes
int factorial(int n);
char* create_string(const char* input);

int main(int argc, char **argv) {
    // Local variables
    int numbers[] = {1, 2, 3, 4, 5};
    Record record = {.id = 42, .name = "test", .value = 3.14f};

    printf("Hello, World!\n");
    printf("Record: id=%d, name=%s, value=%.2f\n", 
           record.id, record.name, record.value);

    // Control structures
    for (int i = 0; i < 5; i++) {
        if (numbers[i] % 2 == 0) {
            printf("Even: %d\n", numbers[i]);
        } else {
            printf("Odd: %d\n", numbers[i]);
        }
    }

    // Function call
    int result = factorial(5);
    printf("Factorial of 5: %d\n", result);

    return EXIT_SUCCESS;
}

int factorial(int n) {
    return (n <= 1) ? 1 : n * factorial(n - 1);
}

char* create_string(const char* input) {
    char* result = malloc(strlen(input) + 1);
    if (result != NULL) {
        strcpy(result, input);
    }
    return result;
}
