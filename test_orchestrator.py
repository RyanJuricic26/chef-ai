"""
Test script for the orchestrator workflow
"""
from agents.orchestrator.graph import graph


def test_orchestrator(user_input: str):
    """Test the orchestrator with a user input"""
    print(f"\n{'='*60}")
    print(f"User Input: {user_input}")
    print(f"{'='*60}\n")

    # Run the orchestrator
    result = graph.invoke({"user_input": user_input})

    # Print results
    print(f"Intent: {result.get('intent')}")
    print(f"Success: {result.get('success')}")

    if result.get('error_message'):
        print(f"Error: {result.get('error_message')}")

    print(f"\nResponse:")
    print("-" * 60)
    print(result.get('response'))
    print("\n")

    return result


if __name__ == "__main__":
    # Test different scenarios

    print("\n" + "="*60)
    print("TESTING ORCHESTRATOR WORKFLOW")
    print("="*60)

    # Test 1: Fetch recipes by ingredients
    test_orchestrator("I have chicken, soy sauce, and rice. What can I make?")

    # Test 2: Fetch recipes by name
    test_orchestrator("Show me a recipe for tacos")

    # Test 3: General recipe search
    test_orchestrator("What Italian recipes do you have?")

    # Test 4: Catalog a recipe (will fail without real URL and implementation)
    test_orchestrator("Add this recipe: https://example.com/amazing-pasta")

    # Test 5: Catalog recipe different phrasing
    test_orchestrator("Can you save https://food.com/chocolate-cake to the database?")
