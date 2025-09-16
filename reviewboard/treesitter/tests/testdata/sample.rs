use std::collections::HashMap;
use std::fmt::Display;

/// Documentation comment for Person struct
#[derive(Debug, Clone)]
pub struct Person {
    pub name: String,
    pub age: u32,
    email: Option<String>,
}

// Trait definition
trait Greet {
    fn greet(&self) -> String;
}

impl Greet for Person {
    fn greet(&self) -> String {
        format!("Hello, my name is {}", self.name)
    }
}

impl Person {
    /// Creates a new Person
    pub fn new(name: String, age: u32) -> Self {
        Person {
            name,
            age,
            email: None,
        }
    }

    pub fn set_email(&mut self, email: String) {
        self.email = Some(email);
    }
}

// Generic function
fn process_data<T: Display>(data: Vec<T>) -> String {
    data.iter()
        .map(|item| item.to_string())
        .collect::<Vec<_>>()
        .join(", ")
}

fn main() {
    let mut people: HashMap<u32, Person> = HashMap::new();

    // Creating instances
    let mut person1 = Person::new("Alice".to_string(), 30);
    person1.set_email("alice@example.com".to_string());

    let person2 = Person {
        name: "Bob".into(),
        age: 25,
        email: Some("bob@test.com".to_string()),
    };

    people.insert(1, person1);
    people.insert(2, person2);

    // Pattern matching
    for (id, person) in &people {
        match &person.email {
            Some(email) => println!("ID {}: {} ({})", id, person.greet(), email),
            None => println!("ID {}: {} (no email)", id, person.greet()),
        }
    }

    // Closure and iterator
    let ages: Vec<u32> = people
        .values()
        .filter(|p| p.age > 25)
        .map(|p| p.age)
        .collect();

    println!("Ages over 25: {}", process_data(ages));

    // Error handling
    let result = divide(10.0, 2.0);
    match result {
        Ok(value) => println!("Result: {}", value),
        Err(e) => eprintln!("Error: {}", e),
    }
}

fn divide(a: f64, b: f64) -> Result<f64, &'static str> {
    if b == 0.0 {
        Err("Division by zero")
    } else {
        Ok(a / b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_person_creation() {
        let person = Person::new("Test".to_string(), 20);
        assert_eq!(person.name, "Test");
        assert_eq!(person.age, 20);
    }
}
