import pytest
import sqlite3
from contextlib import contextmanager
import re
import logging

from meal_max.models.kitchen_model import Meal
from meal_max.models.kitchen_model import (create_meal, delete_meal, get_leaderboard, get_meal_by_id, get_meal_by_name, update_meal_stats)

from meal_max.utils.logger import configure_logger


logger = logging.getLogger(__name__)
configure_logger(logger)

def normalize_whitespace(sql_query: str) -> str:
    """Normalize whitespace in SQL queries for consistent comparison."""
    return re.sub(r'\s+', ' ', sql_query).strip()

##################################################
# Fixtures
##################################################

@pytest.fixture
def mock_cursor(mocker):
    """
    Fixture that provides a mock database cursor and connection for testing.
    Mocks the database connection context manager to avoid actual database operations.
    """
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_cursor.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("meal_max.models.kitchen_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test

##################################################
# Meal Class Initialization Test Cases
##################################################

def test_post_init_valid_price():
    """Test creating a Meal object with valid price and difficulty."""
    meal = Meal(1, "meal", "cuisine", 1, "LOW")
    assert meal.price == 1
    assert meal.difficulty == 'LOW'

def test_post_init_negative_price():
    """Test that creating a Meal with negative price raises ValueError."""
    with pytest.raises(ValueError, match="Price must be a positive value."):
        Meal(1, "meal", "cuisine", -1, "LOW")

def test_meal_with_invalid_difficulty():
    """Test that creating a Meal with invalid difficulty raises ValueError."""
    with pytest.raises(ValueError, match="Difficulty must be 'LOW', 'MED', or 'HIGH'."):
        Meal(1, "meal", "cuisine", 1, "EASY")

def test_meal_with_valid_high_difficulty():
    """Test creating a Meal object with HIGH difficulty level."""
    meal = Meal(1, "meal", "cuisine", 1, "HIGH")
    assert meal.price == 1
    assert meal.difficulty == 'HIGH'

##################################################
# Create Meal Test Cases
##################################################

def test_create_success(mock_cursor):
    """Test successful meal creation with valid parameters."""
    create_meal(meal="meal", cuisine="cuisine", price=1.0, difficulty="LOW")

    expected_query = normalize_whitespace("""
        INSERT INTO meals (meal, cuisine, price, difficulty)
        VALUES (?, ?, ?, ?)
    """)
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args[0][1]
    expected_arguments = ("meal", "cuisine", 1.0, "LOW")
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_create_meal_duplicate(mock_cursor):
    """Test that creating a duplicate meal raises ValueError."""
    mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed: meal.names")

    with pytest.raises(ValueError, match="Meal with name 'meal' already exists"):
        create_meal(meal="meal", cuisine="cuisine", price=1.0, difficulty="LOW")

def test_create_meal_with_invalid_price():
    """Test that creating a meal with invalid price raises ValueError."""
    with pytest.raises(ValueError, match="Invalid price: 0.0. Price must be a positive number."):
        create_meal(meal="Pizza", cuisine="Italian", price=0.0, difficulty="MED")

    with pytest.raises(ValueError, match="Invalid price: invalid. Price must be a positive number."):
        create_meal(meal="Pizza", cuisine="Italian", price='invalid', difficulty="MED")

def test_create_meal_with_invalid_difficulty():
    """Test that creating a meal with invalid difficulty raises ValueError."""
    with pytest.raises(ValueError, match="Invalid difficulty level: EASY. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal(meal="Pizza", cuisine="Italian", price=1.0, difficulty="EASY")
    
    with pytest.raises(ValueError, match="Invalid difficulty level: 3. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal(meal="Pizza", cuisine="Italian", price=1.0, difficulty=3)

##################################################
# Delete Meal Test Cases
##################################################

def test_delete_meal(mock_cursor):
    """Test successful meal deletion."""
    mock_cursor.fetchone.return_value = ([False])

    delete_meal(1)

    expected_select_sql = normalize_whitespace("SELECT deleted FROM meals WHERE id = ?")
    expected_update_sql = normalize_whitespace("UPDATE meals SET deleted = TRUE WHERE id = ?")

    actual_select_sql = normalize_whitespace(mock_cursor.execute.call_args_list[0][0][0])
    actual_update_sql = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    assert actual_select_sql == expected_select_sql, "The SELECT query did not match the expected structure."
    assert actual_update_sql == expected_update_sql, "The UPDATE query did not match the expected structure."

    actual_select_args = mock_cursor.execute.call_args_list[0][0][1]
    actual_update_args = mock_cursor.execute.call_args_list[1][0][1]
    expected_args = (1,)

    assert actual_select_args == expected_args, f"The SELECT query arguments did not match. Expected {expected_args}, got {actual_select_args}."
    assert actual_update_args == expected_args, f"The UPDATE query arguments did not match. Expected {expected_args}, got {actual_update_args}."

def test_delete_nonexistent_meal_id(mock_cursor):
    """Test that deleting a nonexistent meal raises ValueError."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        delete_meal(999)

def test_delete_meal_already_deleted(mock_cursor):
    """Test that deleting an already deleted meal raises ValueError."""
    mock_cursor.fetchone.return_value = ([True])

    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        delete_meal(999)

##################################################
# Get Leaderboard Test Cases
##################################################

def test_get_leaderboard_success(mock_cursor):
    """Test successful retrieval of the meal leaderboard."""
    mock_cursor.fetchall.return_value = [
        (3, "Meal C", "Cuisine C", 3.0, "HIGH", 3, 3.0, 1.0, False),
        (2, "Meal B", "Cuisine B", 2.0, "MED", 2, 2.0, 1.0, False),
        (1, "Meal A", "Cuisine A", 1.0, "LOW", 1, 1.0, 1.0, False)
    ]

    leaderboard = get_leaderboard()

    expected_result = [
        {"id": 3, "meal": "Meal C", "cuisine": "Cuisine C", "price": 3.0, "difficulty": "HIGH", "battles": 3, "wins": 3.0, "win_pct": 100.0},
        {"id": 2, "meal": "Meal B", "cuisine": "Cuisine B", "price": 2.0, "difficulty": "MED", "battles": 2, "wins": 2.0, "win_pct": 100.0},
        {"id": 1, "meal": "Meal A", "cuisine": "Cuisine A", "price": 1.0, "difficulty": "LOW", "battles": 1, "wins": 1.0, "win_pct": 100.0},
    ]

    assert leaderboard == expected_result, f"Expected {expected_result}, but got {leaderboard}"

    expected_query = normalize_whitespace("""
        SELECT id, meal, cuisine, price, difficulty, battles, wins, (wins * 1.0 / battles) AS win_pct
        FROM meals WHERE deleted = false AND battles > 0
    """ + " ORDER BY wins DESC")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

def test_get_leaderboard_invalid_sort_by():
    """Test that getting leaderboard with invalid sort parameter raises ValueError."""
    with pytest.raises(ValueError, match="Invalid sort_by parameter: param"):
        get_leaderboard(sort_by="param")

##################################################
# Meal Retrieval Test Cases
##################################################

def test_get_meal_by_id(mock_cursor):
    """Test successful meal retrieval by ID."""
    mock_cursor.fetchone.return_value = (1, "Meal A", "Cuisine A", 1.0, "LOW", False)

    result = get_meal_by_id(1)
    expected_result = Meal(1, "Meal A", "Cuisine A", 1.0, "LOW")

    assert result == expected_result, f"Expected {expected_result}, got {result}"

    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args[0][1]
    expected_arguments = (1,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_get_meal_by_id_bad_id(mock_cursor):
    """Test that retrieving a meal with invalid ID raises ValueError."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        get_meal_by_id(999)

def test_get_meal_by_name_success(mock_cursor):
    """Test successful meal retrieval by name."""
    mock_cursor.fetchone.return_value = (1, "Meal A", "Cuisine A", 1.0, "LOW", False)

    result = get_meal_by_name('Meal A')
    expected_result = Meal(1, "Meal A", "Cuisine A", 1.0, "LOW")

    assert result == expected_result, f"Expected {expected_result}, got {result}"

    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE meal = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args[0][1]
    expected_arguments = ('Meal A',)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_get_meal_by_name_bad_name(mock_cursor):
    """Test that retrieving a meal with invalid name raises ValueError."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with name food not found"):
        get_meal_by_name('food')

##################################################
# Meal Statistics Test Cases
##################################################

def test_update_meal_stats_win(mock_cursor):
    """Test successful update of meal statistics for a win."""
    mock_cursor.fetchone.return_value = [False]

    meal_id = 1
    update_meal_stats(meal_id, 'win')

    expected_query = normalize_whitespace("""
        UPDATE meals SET battles = battles + 1, wins = wins + 1 WHERE id = ?
    """)
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]
    expected_arguments = (meal_id,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_update_meal_stats_loss(mock_cursor):
    """Test successful update of meal statistics for a loss."""
    mock_cursor.fetchone.return_value = [False]

    meal_id = 1
    update_meal_stats(meal_id, 'loss')

    expected_query = normalize_whitespace("""
        UPDATE meals SET battles = battles + 1 WHERE id = ?
    """)
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]
    expected_arguments = (meal_id,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_update_meal_stats_deleted_meal(mock_cursor):
    """Test that updating stats for a deleted meal raises ValueError."""
    mock_cursor.fetchone.return_value = [True]

    with pytest.raises(ValueError, match="Meal with ID 1 has been deleted"):
        update_meal_stats(1, 'win')

    mock_cursor.execute.assert_called_once_with("SELECT deleted FROM meals WHERE id = ?", (1,))

def test_update_meal_stats_bad_meal(mock_cursor):
    """Test that updating stats for a nonexistent meal raises ValueError."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        update_meal_stats(999, 'win')

def test_update_meal_stats_invalid_result(mock_cursor):
    """Test that updating stats with invalid result raises ValueError."""
    mock_cursor.fetchone.return_value = [False]

    with pytest.raises(ValueError, match="Invalid result: invalid. Expected 'win' or 'loss'."):
        update_meal_stats(1, 'invalid')

    mock_cursor.execute.assert_called_once_with("SELECT deleted FROM meals WHERE id = ?", (1,))