"""
Test script for the fetch_recipes workflow
"""
from agents.fetch_recipes.graph import graph, AgentState


def test_workflow(query: str):
    """Test the fetch_recipes workflow with a query"""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")

    # Create initial state
    initial_state = AgentState(user_query=query)

    # Run the workflow
    result = graph.invoke(initial_state)

    # Print results
    print("Search Mode:", result.search_mode)
    if result.user_ingredients:
        print("Detected Ingredients:", ", ".join(result.user_ingredients))
    print(f"\nFound {len(result.recipes)} total recipes")
    print(f"Filtered to {len(result.filtered_recipes)} recipes\n")

    print("RECOMMENDATIONS:")
    print("-" * 60)
    print(result.recommendations)
    print("\n")


if __name__ == "__main__":
    # Test different query types

    # Test 1: Ingredient-based search
    test_workflow("I have chicken, soy sauce, bell peppers, and rice. What can I make?")

    # Test 2: Name-based search
    test_workflow("Show me a recipe for tacos")

    # Test 3: General search
    test_workflow("What Italian recipes do you have?")

    # Test 4: Another ingredient search
    test_workflow("I've got tomatoes, mozzarella, and basil in my fridge")
