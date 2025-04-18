Feature: Todo List Management
  As a user
  I want to manage my todo items
  So that I can keep track of my tasks

  Scenario: Create a new todo item
    Given I am on the todo application
    When I enter a new todo item "Buy groceries"
    And I click the add button
    Then I should see "Buy groceries" in the todo list

  