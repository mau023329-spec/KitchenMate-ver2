```python
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time
import random

# Constants
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_WIDTH = 50
PIPE_GAP = 150
PIPE_FREQUENCY = 150
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600

# Initialize game state
def init_game():
    st.session_state.bird_y = SCREEN_HEIGHT // 2
    st.session_state.bird_velocity = 0
    st.session_state.pipes = []
    st.session_state.score = 0
    st.session_state.game_over = False
    st.session_state.last_pipe = 0
    st.session_state.last_update = time.time()

# Create a new pipe
def create_pipe():
    pipe_height = random.randint(100, SCREEN_HEIGHT - 100 - PIPE_GAP)
    return {
        'x': SCREEN_WIDTH,
        'top_height': pipe_height,
        'bottom_y': pipe_height + PIPE_GAP
    }

# Update game state
def update_game():
    current_time = time.time()
    delta_time = current_time - st.session_state.last_update
    st.session_state.last_update = current_time

    # Update bird position
    st.session_state.bird_velocity += GRAVITY * delta_time
    st.session_state.bird_y += st.session_state.bird_velocity

    # Check for collisions with ground or ceiling
    if st.session_state.bird_y <= 0 or st.session_state.bird_y >= SCREEN_HEIGHT:
        st.session_state.game_over = True

    # Generate new pipes
    if len(st.session_state.pipes) == 0 or st.session_state.pipes[-1]['x'] < SCREEN_WIDTH - PIPE_FREQUENCY:
        st.session_state.pipes.append(create_pipe())

    # Update pipe positions
    for pipe in st.session_state.pipes:
        pipe['x'] -= 2 * delta_time * 60  # Adjust speed as needed

        # Check for collisions with pipes
        if (SCREEN_WIDTH // 2 - 15 <= pipe['x'] + PIPE_WIDTH and
            SCREEN_WIDTH // 2 + 15 >= pipe['x'] and
            (st.session_state.bird_y - 15 <= pipe['top_height'] or
             st.session_state.bird_y + 15 >= pipe['bottom_y'])):
            st.session_state.game_over = True

        # Check if pipe passed
        if pipe['x'] + PIPE_WIDTH < SCREEN_WIDTH // 2 and not pipe.get('passed', False):
            pipe['passed'] = True
            st.session_state.score += 1

    # Remove off-screen pipes
    st.session_state.pipes = [pipe for pipe in st.session_state.pipes if pipe['x'] > -PIPE_WIDTH]

# Draw the game
def draw_game():
    fig, ax = plt.subplots(figsize=(SCREEN_WIDTH/100, SCREEN_HEIGHT/100))
    ax.set_xlim(0, SCREEN_WIDTH)
    ax.set_ylim(0, SCREEN_HEIGHT)
    ax.set_aspect('equal')
    ax.axis('off')

    # Draw background
    ax.add_patch(patches.Rectangle((0, 0), SCREEN_WIDTH, SCREEN_HEIGHT, color='skyblue'))

    # Draw pipes
    for pipe in st.session_state.pipes:
        # Top pipe
        ax.add_patch(patches.Rectangle(
            (pipe['x'], pipe['top_height']),
            PIPE_WIDTH, SCREEN_HEIGHT - pipe['top_height'],
            color='green'
        ))
        # Bottom pipe
        ax.add_patch(patches.Rectangle(
            (pipe['x'], 0),
            PIPE_WIDTH, pipe['bottom_y'],
            color='green'
        ))

    # Draw bird
    ax.add_patch(patches.Circle((SCREEN_WIDTH // 2, st.session_state.bird_y), 15, color='yellow'))

    # Draw score
    ax.text(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, f'Score: {st.session_state.score}',
            ha='center', va='center', fontsize=20, color='white')

    # Draw game over message if needed
    if st.session_state.game_over:
        ax.text(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 'Game Over!',
                ha='center', va='center', fontsize=30, color='red')

    plt.tight_layout()
    st.pyplot(fig)

# Main game function
def flappy_bird():
    st.title("Flappy Bird")

    # Initialize game if not already done
    if 'bird_y' not in st.session_state:
        init_game()

    # Draw the game
    draw_game()

    # Game controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Flap"):
            if not st.session_state.game_over:
                st.session_state.bird_velocity = FLAP_STRENGTH
    with col2:
        if st.button("Restart"):
            init_game()

    # Update game state
    if not st.session_state.game_over:
        update_game()
        time.sleep(0.01)  # Small delay to make the game playable
        st.experimental_rerun()

# Run the game
if __name__ == "__main__":
    flappy_bird()
```
