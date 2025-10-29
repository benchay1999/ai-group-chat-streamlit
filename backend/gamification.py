"""
Gamification system for user engagement.
Defines achievements, points calculation, and level progression.
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Achievement:
    """Achievement definition."""
    id: str
    name: str
    description: str
    points: int
    icon: str  # Icon name or emoji
    requirement_type: str  # "games_played", "wins", "streak", "accuracy"
    requirement_value: int


# Achievement definitions
ACHIEVEMENTS = [
    # Games played milestones
    Achievement("first_game", "First Steps", "Complete your first game", 10, "🎮", "games_played", 1),
    Achievement("games_5", "Getting Started", "Play 5 games", 25, "🎯", "games_played", 5),
    Achievement("games_10", "Regular Player", "Play 10 games", 50, "⭐", "games_played", 10),
    Achievement("games_25", "Experienced", "Play 25 games", 100, "🏆", "games_played", 25),
    Achievement("games_50", "Veteran", "Play 50 games", 200, "🎖️", "games_played", 50),
    Achievement("games_100", "Centurion", "Play 100 games", 500, "👑", "games_played", 100),
    
    # Win milestones
    Achievement("first_win", "Sharp Eye", "Win your first game", 20, "👁️", "wins", 1),
    Achievement("wins_5", "Detective", "Win 5 games", 50, "🔍", "wins", 5),
    Achievement("wins_10", "Expert Hunter", "Win 10 games", 100, "🎯", "wins", 10),
    Achievement("wins_25", "AI Whisperer", "Win 25 games", 250, "🧠", "wins", 25),
    
    # Streak milestones
    Achievement("streak_3", "Consistent", "Play 3 days in a row", 30, "📅", "streak", 3),
    Achievement("streak_7", "Dedicated", "Play 7 days in a row", 70, "🔥", "streak", 7),
    Achievement("streak_14", "Committed", "Play 14 days in a row", 150, "💪", "streak", 14),
    Achievement("streak_30", "Unstoppable", "Play 30 days in a row", 300, "⚡", "streak", 30),
    
    # Win rate milestones (calculated separately)
    Achievement("accuracy_50", "Better Than Chance", "50% win rate (min 10 games)", 100, "🎲", "accuracy", 50),
    Achievement("accuracy_70", "Master Detective", "70% win rate (min 20 games)", 200, "🕵️", "accuracy", 70),
    Achievement("accuracy_90", "AI Terminator", "90% win rate (min 30 games)", 500, "🤖", "accuracy", 90),
]


def calculate_level(total_points: int) -> int:
    """
    Calculate user level based on total points.
    Level progression: Level N requires 100 * N^1.5 total points
    
    Args:
        total_points: Total points accumulated
        
    Returns:
        User level (1+)
    """
    if total_points < 100:
        return 1
    
    # Binary search for level
    level = 1
    while True:
        required_points = int(100 * (level ** 1.5))
        if total_points < required_points:
            return level
        level += 1
        if level > 100:  # Cap at level 100
            return 100


def points_for_next_level(current_level: int) -> int:
    """
    Calculate points needed for next level.
    
    Args:
        current_level: Current user level
        
    Returns:
        Total points needed to reach next level
    """
    next_level = current_level + 1
    return int(100 * (next_level ** 1.5))


def calculate_game_points(
    game_completed: bool = True,
    won_game: bool = False,
    discussion_duration: int = 180,
    num_messages: int = 0,
    voted: bool = False
) -> Tuple[int, Dict[str, int]]:
    """
    Calculate points earned from a game.
    
    Args:
        game_completed: Whether the game was completed
        won_game: Whether user correctly identified AI
        discussion_duration: Length of discussion in seconds
        num_messages: Number of messages user sent
        voted: Whether user voted
        
    Returns:
        Tuple of (total_points, breakdown_dict)
    """
    breakdown = {}
    
    # Base completion points
    if game_completed:
        breakdown["completion"] = 10
    
    # Win bonus
    if won_game:
        breakdown["win"] = 50
    
    # Participation bonus (based on messages sent)
    if num_messages >= 5:
        breakdown["active_participation"] = 20
    elif num_messages >= 3:
        breakdown["participation"] = 10
    
    # Voting bonus
    if voted:
        breakdown["voted"] = 5
    
    # Time bonus (staying for full duration)
    if discussion_duration >= 180:  # 3+ minutes
        breakdown["time_commitment"] = 10
    
    total_points = sum(breakdown.values())
    return total_points, breakdown


def check_achievements(
    user_total_games: int,
    user_total_wins: int,
    user_current_streak: int,
    user_total_points: int,
    previous_achievements: List[str]
) -> List[Achievement]:
    """
    Check for newly unlocked achievements.
    
    Args:
        user_total_games: Total games played by user
        user_total_wins: Total wins by user
        user_current_streak: Current consecutive days streak
        user_total_points: Total points accumulated
        previous_achievements: List of already unlocked achievement IDs
        
    Returns:
        List of newly unlocked achievements
    """
    newly_unlocked = []
    
    for achievement in ACHIEVEMENTS:
        # Skip if already unlocked
        if achievement.id in previous_achievements:
            continue
        
        # Check requirement
        unlocked = False
        
        if achievement.requirement_type == "games_played":
            unlocked = user_total_games >= achievement.requirement_value
        
        elif achievement.requirement_type == "wins":
            unlocked = user_total_wins >= achievement.requirement_value
        
        elif achievement.requirement_type == "streak":
            unlocked = user_current_streak >= achievement.requirement_value
        
        elif achievement.requirement_type == "accuracy":
            if user_total_games >= 10:  # Minimum games for accuracy achievements
                win_rate = (user_total_wins / user_total_games) * 100
                # Check minimum games for higher tiers
                min_games_required = 10 if achievement.requirement_value <= 50 else (20 if achievement.requirement_value <= 70 else 30)
                if user_total_games >= min_games_required:
                    unlocked = win_rate >= achievement.requirement_value
        
        if unlocked:
            newly_unlocked.append(achievement)
    
    return newly_unlocked


def update_streak(last_played_at: datetime, current_streak: int, longest_streak: int) -> Tuple[int, int]:
    """
    Update user's play streak based on last play date.
    
    Args:
        last_played_at: Last time user played (None if first time)
        current_streak: Current streak count
        longest_streak: Longest streak ever
        
    Returns:
        Tuple of (new_current_streak, new_longest_streak)
    """
    now = datetime.utcnow()
    
    if last_played_at is None:
        # First game
        return 1, 1
    
    # Calculate days since last play
    days_since = (now.date() - last_played_at.date()).days
    
    if days_since == 0:
        # Same day, keep streak
        return current_streak, longest_streak
    elif days_since == 1:
        # Consecutive day, increment streak
        new_streak = current_streak + 1
        new_longest = max(new_streak, longest_streak)
        return new_streak, new_longest
    else:
        # Streak broken, reset to 1
        return 1, longest_streak


def get_motivational_message(
    user_total_games: int,
    user_total_wins: int,
    user_current_streak: int,
    next_achievements: List[Achievement]
) -> str:
    """
    Generate a motivational message for the user.
    
    Args:
        user_total_games: Total games played
        user_total_wins: Total wins
        user_current_streak: Current streak
        next_achievements: Upcoming achievements user can unlock
        
    Returns:
        Motivational message string
    """
    if not next_achievements:
        return "You're doing great! Keep playing to maintain your streak! 🎮"
    
    # Find the closest achievement
    next_achievement = next_achievements[0]
    
    if next_achievement.requirement_type == "games_played":
        games_needed = next_achievement.requirement_value - user_total_games
        return f"Play {games_needed} more {'game' if games_needed == 1 else 'games'} to unlock '{next_achievement.name}'! {next_achievement.icon}"
    
    elif next_achievement.requirement_type == "wins":
        wins_needed = next_achievement.requirement_value - user_total_wins
        return f"Win {wins_needed} more {'game' if wins_needed == 1 else 'games'} to unlock '{next_achievement.name}'! {next_achievement.icon}"
    
    elif next_achievement.requirement_type == "streak":
        days_needed = next_achievement.requirement_value - user_current_streak
        return f"Play {days_needed} more consecutive {'day' if days_needed == 1 else 'days'} to unlock '{next_achievement.name}'! {next_achievement.icon}"
    
    return "Keep playing to unlock more achievements! 🏆"


def get_next_close_achievements(
    user_total_games: int,
    user_total_wins: int,
    user_current_streak: int,
    unlocked_achievement_ids: List[str],
    limit: int = 3
) -> List[Tuple[Achievement, int]]:
    """
    Get the next closest achievements the user can unlock.
    
    Args:
        user_total_games: Total games played
        user_total_wins: Total wins
        user_current_streak: Current streak
        unlocked_achievement_ids: Already unlocked achievement IDs
        limit: Maximum number of achievements to return
        
    Returns:
        List of tuples (achievement, progress_needed)
    """
    candidates = []
    
    for achievement in ACHIEVEMENTS:
        if achievement.id in unlocked_achievement_ids:
            continue
        
        progress_needed = 0
        
        if achievement.requirement_type == "games_played":
            progress_needed = achievement.requirement_value - user_total_games
        elif achievement.requirement_type == "wins":
            progress_needed = achievement.requirement_value - user_total_wins
        elif achievement.requirement_type == "streak":
            progress_needed = achievement.requirement_value - user_current_streak
        elif achievement.requirement_type == "accuracy":
            # Skip accuracy achievements for "next close" as they're conditional
            continue
        
        if progress_needed > 0:
            candidates.append((achievement, progress_needed))
    
    # Sort by progress needed (closest first)
    candidates.sort(key=lambda x: x[1])
    
    return candidates[:limit]

