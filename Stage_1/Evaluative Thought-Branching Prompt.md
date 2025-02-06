Your goal is to arrive at a solution through a series of reasoning steps.  You will generate thoughts, evaluate them, and build upon the best ones.  You should aim to complete your reasoning in approximately [NUMBER] steps.

**Reasoning Process:**

1.  **Initial Thought:** Begin by stating your initial understanding of the problem and a potential first step.

2.  **Iterative Thought Generation:** For each subsequent step, generate *multiple* (at least 3) distinct thoughts.  Each thought should build upon previous thoughts, explore different approaches, or refine existing ideas.  Consider these factors for *each* thought:

    *   **Thought:** [Clearly state the reasoning step in complete sentences.]
    *   **Logical Score (0-1):**  Rate the logical soundness and clarity of this thought.  Higher scores for well-formed, relevant reasoning. Consider:
        *   Does it use logical connectors (therefore, because, if...then, so)?
        *   Does it contain relevant mathematical/logical expressions if applicable?
        *   Is it coherent with the previous thought (if applicable)?
    *   **Depth Penalty (0-1):**  Estimate how far along you are in the reasoning process.  A lower score indicates you are closer to the expected number of steps. Calculate as: 1 - (current step / total steps).
    *   **Completion Bonus (0 or 0.2):**  If this thought represents a complete and satisfactory solution, give it a bonus of 0.2. Otherwise, 0.
    *   **Overall Score (0-1):** Calculate the overall score as the average of Logical Score, Depth Penalty, and Completion Bonus.
    *   **Policy Score (0-1):** (Advanced - Optional) Rate how promising this thought *feels* based on your intuition and experience.  Consider:
        *   How well does it align with the overall goal?
        *   How novel or unique is this approach compared to previous thoughts? (Higher novelty is generally better, up to a point).
    *   **Value Estimate (0-1):** (Advanced - Optional) Estimate the long-term potential of this thought.  Consider:
        *   How likely is this thought to lead to a solution, even if it requires further steps?
        *   Does it open up new avenues of exploration?
    *   **Action:** (Advanced - Optional) Briefly describe the core action or approach taken in this thought (e.g., "define_variables", "apply_formula", "consider_counterexample").

3.  **Selection:** After generating multiple thoughts for a step, explicitly state which thought you are selecting to build upon in the next step, and *why*.  Prioritize thoughts with higher Overall Scores, and consider Policy Score and Value Estimate if you are using them.

4.  **Termination:** Continue this process until you reach a thought with a Completion Bonus of 0.2, or you reach the expected number of steps.

5. **Bidirectional Approach (Optional):**
    *   **Start Thought:** [Initial thought as above]
    *   **Goal Thought:** [State what a successful solution would look like, or a desired end state.]
    *   **Iterate from Both Ends:** Alternate between generating thoughts that build forward from the Start Thought and backward from the Goal Thought.  Label each thought as either "Forward" or "Backward".  Aim to find a "meeting point" where the forward and backward reasoning chains connect.

**Example (Partial - Step 2, assuming Step 1 has been completed):**

**Step 2:**

**Thought 1:**

*   **Thought:** Let's try to define the key variables in the problem more precisely.
*   **Logical Score:** 0.8
*   **Depth Penalty:** 0.8 (Assuming 5 total steps, and this is step 2: 1 - (2/5) = 0.6, I made a mistake in the prompt, it should be current step -1)
*   **Completion Bonus:** 0
*   **Overall Score:** 0.533
*   **Policy Score:** 0.7
*   **Value Estimate:** 0.6
*   **Action:** define_variables

**Thought 2:**

*   **Thought:** We could try to find a similar problem that has already been solved and adapt the solution.
*   **Logical Score:** 0.7
*   **Depth Penalty:** 0.8
*   **Completion Bonus:** 0
*   **Overall Score:** 0.5
*   **Policy Score:** 0.6
*   **Value Estimate:** 0.8
*   **Action:** find_analogous_problem

**Thought 3:**

*   **Thought:**  Let's list all the given information and constraints.
*   **Logical Score:** 0.9
*   **Depth Penalty:** 0.8
*   **Completion Bonus:** 0
*   **Overall Score:** 0.567
*   **Policy Score:** 0.8
*   **Value Estimate:** 0.7
*   **Action:** list_constraints

**Selection:** I select Thought 3 because it has the highest Overall Score and a high Policy Score, suggesting it's a promising and logical next step. Listing the constraints is a good foundational step for many problem-solving approaches.

**Continue to Step 3, building upon Thought 3...**

---

**Explanation and Variations:**

*   **Core Idea:** The prompt forces the LLM to explicitly generate multiple options, evaluate them based on defined criteria, and justify its selection. This mimics the exploration and exploitation balance of MCTS.
*   **Scoring:** The scoring system (Logical Score, Depth Penalty, Completion Bonus) is a simplified version of the `evaluateThought` function in the codebase.  The "Advanced" Policy Score and Value Estimate are attempts to capture the intuition of the policy and value networks in the MCTS-Alpha variants.
*   **Multiple Thoughts:**  Generating multiple thoughts per step encourages exploration, similar to expanding multiple nodes in MCTS.
*   **Selection:**  The explicit selection step forces the LLM to choose the most promising path, mimicking the selection phase of MCTS.
*   **Bidirectional Approach:** This optional section mimics the `MCTS002AltAlphaStrategy`, encouraging the LLM to work from both the problem statement and the desired solution.
*   **Action:** This helps to categorize the type of reasoning step, similar to the `actionHistory` in the codebase.
*   **Limitations:**
    *   **True Randomness:**  LLMs are not truly random, so the "simulation" aspect of MCTS cannot be perfectly replicated.
    *   **Memory:**  LLMs have limited context windows, making it difficult to maintain a large "search tree" in memory like the codebase does.  The prompt tries to mitigate this by focusing on the current path and its immediate children.
    *   **Policy/Value Networks:**  The Policy Score and Value Estimate are subjective and rely on the LLM's internal knowledge and "intuition."  They are not trained networks like in the codebase.
    *   **Backpropagation:** True backpropagation of rewards is not possible in a single prompt.  The prompt encourages a form of "forward propagation" by having the LLM consider the value estimate of future steps.

*   **Variations:**
    *   **Simplified Version:** Remove the "Advanced" sections (Policy Score, Value Estimate, Action, Bidirectional Approach) for a simpler prompt that still captures the core ideas of Beam Search or basic MCTS.
    *   **Beam Search Focus:**  Instead of asking for "at least 3" thoughts, specify a fixed number (e.g., 3 or 5) and emphasize selecting the top *n* thoughts to continue with, explicitly mimicking a beam.
    *   **More Detailed Scoring:** Provide more specific guidelines for calculating the Logical Score, perhaps breaking it down into sub-criteria.
    *   **Problem-Specific Guidance:**  Tailor the prompt to the specific problem by suggesting relevant actions or approaches.
    *   **Iterative Prompting:** Instead of a single, large prompt, you could use a series of shorter prompts, where each prompt builds upon the output of the previous one. This would allow for a more interactive and controlled reasoning process, and better simulate backpropagation. You would manually (or with a script) feed the LLM's output back into a new prompt.