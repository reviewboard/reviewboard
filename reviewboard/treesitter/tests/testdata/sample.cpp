#include <iostream>
#include <vector>
#include <string>
#include <memory>
#include <algorithm>

/**
 * Sample C++ file for TreeSitter testing.
 */

namespace utils {

template<typename T>
class Container {
private:
    std::vector<T> data_;
    size_t capacity_;

public:
    explicit Container(size_t initial_capacity = 10)
        : capacity_(initial_capacity) {
        data_.reserve(initial_capacity);
    }

    ~Container() = default;

    void add(const T& item) {
        if (data_.size() >= capacity_) {
            resize();
        }
        data_.push_back(item);
    }

    void add(T&& item) {
        if (data_.size() >= capacity_) {
            resize();
        }
        data_.push_back(std::move(item));
    }

    [[nodiscard]] size_t size() const noexcept {
        return data_.size();
    }

    [[nodiscard]] bool empty() const noexcept {
        return data_.empty();
    }

    T& at(size_t index) {
        if (index >= data_.size()) {
            throw std::out_of_range("Index out of range");
        }
        return data_[index];
    }

    const T& at(size_t index) const {
        if (index >= data_.size()) {
            throw std::out_of_range("Index out of range");
        }
        return data_[index];
    }

    auto begin() { return data_.begin(); }
    auto end() { return data_.end(); }
    auto begin() const { return data_.begin(); }
    auto end() const { return data_.end(); }

private:
    void resize() {
        capacity_ *= 2;
        data_.reserve(capacity_);
    }
};

} // namespace utils

// Function to demonstrate various C++ features
void demonstrateFeatures() {
    // Smart pointers
    auto container = std::make_unique<utils::Container<std::string>>();

    // Lambda expressions
    auto print_item = [](const std::string& item) {
        std::cout << "Item: " << item << std::endl;
    };

    // Range-based for loops
    std::vector<std::string> items = {"hello", "world", "test", "example"};
    for (const auto& item : items) {
        container->add(item);
    }

    // STL algorithms
    std::sort(items.begin(), items.end());

    // Auto type deduction
    auto found = std::find(items.begin(), items.end(), "test");
    if (found != items.end()) {
        std::cout << "Found: " << *found << std::endl;
    }

    // Range-based for with container
    std::cout << "Container contents:" << std::endl;
    for (const auto& item : *container) {
        print_item(item);
    }

    // Exception handling
    try {
        auto item = container->at(100);  // This will throw
    } catch (const std::out_of_range& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

int main() {
    std::cout << "C++ TreeSitter Test" << std::endl;

    demonstrateFeatures();

    return 0;
}
