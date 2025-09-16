package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"sync"
	"time"
)

// Constants
const (
	MaxWorkers = 10
	APIVersion = "v1"
)

// Person represents a person with basic information
type Person struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email,omitempty"`
	Age   int    `json:"age"`
}

// PersonService handles person-related operations
type PersonService struct {
	mu     sync.RWMutex
	people map[int]*Person
	nextID int
}

// NewPersonService creates a new PersonService
func NewPersonService() *PersonService {
	return &PersonService{
		people: make(map[int]*Person),
		nextID: 1,
	}
}

// AddPerson adds a new person and returns their ID
func (ps *PersonService) AddPerson(name, email string, age int) int {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	id := ps.nextID
	ps.people[id] = &Person{
		ID:    id,
		Name:  name,
		Email: email,
		Age:   age,
	}
	ps.nextID++
	return id
}

// GetPerson retrieves a person by ID
func (ps *PersonService) GetPerson(id int) (*Person, bool) {
	ps.mu.RLock()
	defer ps.mu.RUnlock()

	person, exists := ps.people[id]
	return person, exists
}

// GetAllPeople returns all people
func (ps *PersonService) GetAllPeople() []*Person {
	ps.mu.RLock()
	defer ps.mu.RUnlock()

	people := make([]*Person, 0, len(ps.people))
	for _, person := range ps.people {
		people = append(people, person)
	}
	return people
}

// HTTP handlers
func (ps *PersonService) handleGetPerson(w http.ResponseWriter, r *http.Request) {
	idStr := r.URL.Query().Get("id")
	if idStr == "" {
		http.Error(w, "ID parameter required", http.StatusBadRequest)
		return
	}

	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, "Invalid ID format", http.StatusBadRequest)
		return
	}

	person, exists := ps.GetPerson(id)
	if !exists {
		http.Error(w, "Person not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(person); err != nil {
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
		return
	}
}

func (ps *PersonService) handleGetAllPeople(w http.ResponseWriter, r *http.Request) {
	people := ps.GetAllPeople()

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(people); err != nil {
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
		return
	}
}

// Worker pool example
func processData(data []int, workers int) []int {
	jobs := make(chan int, len(data))
	results := make(chan int, len(data))

	// Start workers
	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for num := range jobs {
				// Simulate some processing
				time.Sleep(time.Millisecond * 10)
				results <- num * num
			}
		}()
	}

	// Send jobs
	go func() {
		defer close(jobs)
		for _, num := range data {
			jobs <- num
		}
	}()

	// Close results channel when workers are done
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	var processed []int
	for result := range results {
		processed = append(processed, result)
	}

	return processed
}

func main() {
	service := NewPersonService()

	// Add some test data
	service.AddPerson("Alice Johnson", "alice@example.com", 30)
	service.AddPerson("Bob Smith", "bob@test.com", 25)
	service.AddPerson("Carol Davis", "", 35)

	// Set up HTTP routes
	http.HandleFunc("/person", service.handleGetPerson)
	http.HandleFunc("/people", service.handleGetAllPeople)

	// Example of processing data with goroutines
	testData := []int{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
	processed := processData(testData, 3)
	fmt.Printf("Processed data: %v\n", processed)

	// Start server
	fmt.Printf("Server starting on :8080 (API %s)\n", APIVersion)
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal("Server failed to start:", err)
	}
}
