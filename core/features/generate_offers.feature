Feature: Generate trade-up offers
    As an engine user
    I want to generate offers for a customer
    So that I can review options

    Scenario: basic offer generation
        Given a sample customer and inventory
        When the engine generates offers
        Then at least one offer is returned
