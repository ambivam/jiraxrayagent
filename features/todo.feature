Feature: Todo List Management
  As a user
  I want to manage my todo items
  So that I can keep track of my tasks

  Scenario: Create a new todo item
    Given I am on the todo application
    When I enter a new todo item "Buy groceries"
    And I click the add button
    Then I should see "Buy groceries" in the todo list

  Scenario: Mark todo item as complete
    Given I have a todo item "Buy groceries"
    When I click the checkbox next to "Buy groceries"
    Then the item "Buy groceries" should be marked as complete

  Scenario: Edit existing todo item
    Given I have a todo item "Buy groceries"
    When I double click on "Buy groceries"
    And I change the text to "Buy organic groceries"
    And I press Enter
    Then I should see "Buy organic groceries" in the todo list

  Scenario: Delete a todo item
    Given I have a todo item "Buy groceries"
    When I hover over "Buy groceries"
    And I click the delete button
    Then "Buy groceries" should be removed from the todo list

  Scenario: Filter active todos
    Given I have the following todos:
      | Task           | Status    |
      | Buy groceries  | complete  |
      | Clean house    | active    |
      | Pay bills      | active    |
    When I click on "Active" filter
    Then I should only see active todos
    And I should see 2 items in the list

  Scenario: Clear completed todos
    Given I have some completed todo items
    When I click "Clear completed"
    Then all completed items should be removed
    And only active items should remain in the list
