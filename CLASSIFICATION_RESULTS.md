# Question Classification Results

## Overview

This document tracks the results of running the `classify_questions` management command, which uses AI to automatically assign classifications to questions based on their content.

## Command Usage

```bash
# Run on Heroku
heroku run "python manage.py classify_questions --only-unclassified" -a keuvi

# Run locally
python manage.py classify_questions --only-unclassified

# Dry run (preview without changes)
python manage.py classify_questions --dry-run

# Limit to specific category
python manage.py classify_questions --category math --only-unclassified

# Limit number of questions processed
python manage.py classify_questions --limit 50
```

## Available Classifications

### Reading
- Overarching purpose
- Word-in-context
- Line reading
- Unspecified location
- Use of evidence

### Writing
- Commas
- Colons
- Semicolons
- Dashes and Parentheses
- Apostrophes
- Problematic Possessives
- Pronouns
- Who vs. Whom
- Verbs
- Weird Verbs
- Surprising Singularity
- Parallel Structure
- Misplaced Modifiers
- Lightning Round
- Insertions, Deletions, and Revisions
- Introductions, Transitions, and Conclusions
- Moving Sentences
- Transitional Expressions
- Combining Sentences
- Function, Tone, and Phrasing

### Math
- Proportions
- Probabilities
- Mean, Median, Mode, and Range
- Stats
- Exponents and Radicals
- Equations
- Fun with Functions
- Linear Equations
- Quadratic Functions
- Factoring Practice
- Quadratic Formula
- Systems of Equations
- Inequalities
- Exponential Growth and Decay
- Circles
- Triangles
- Missing Angles
- 3D shapes
- Word Problems

---

## Run History

### Run: 2026-01-17 (Heroku - keuvi)

**Command:** `heroku run "python manage.py classify_questions --only-unclassified" -a keuvi`

**Results:**
- Lesson Questions: Classified (count varies based on unclassified)
- Passage Questions: 131 classified

**Notes:**
- Some questions returned "No classifications matched" - may need manual review
- Classifications are assigned based on question text and options content

---

### Template for Future Runs

```
### Run: YYYY-MM-DD (Environment)

**Command:** `<command used>`

**Results:**
- Lesson Questions: X classified
- Passage Questions: Y classified

**Notes:**
- <any observations or issues>
```

rishi@Mac satlingo_backend % heroku run "python manage.py classify_questions --only-unclassified" -a keuvi
Running python manage.py classify_questions --only-unclassified on ⬢ keuvi... up, run.7947
Loaded 44 classifications across 3 categories

=== Processing Lesson Questions ===
Found 416 lesson questions to process

[1/416] Lesson: Introductions, Transitions, and Conclusions, Q1
  Category: writing
  Question: Which of the options provides the best introduction to this paragraph?...
  -> Classifications: ['Introductions, Transitions, and Conclusions']

[2/416] Lesson: Premium Practice #2, Q1
  Category: math
  Question: The solutions to a polynomial equation are -3, -1, and 5. What is the equation?...
  -> Classifications: ['Factoring Practice', 'Equations']

[3/416] Lesson: Premium Practice #1, Q1
  Category: writing
  Question: I want *this, and I want everyone* to want this....
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[4/416] Lesson: Premium Practice #2, Q1
  Category: writing
  Question: The train station— which had no need to be so *beautiful) had* an ornate ceiling....
  -> Classifications: ['Dashes and Parentheses']

[5/416] Lesson: Premium Grammar Practice #1, Q1
  Category: writing
  Question: The students, *many of who* had never seen an extraterrestrial before, crowded around the alien that...
  -> Classifications: ['Pronouns']

[6/416] Lesson: Radicals, Q1
  Category: math
  Question: [[Diagram diagram-31]] = ?...
  -> Classifications: ['Fun with Functions', 'Equations']

[7/416] Lesson: Quick Practice #1, Q1
  Category: writing
  Question: If this world were *mine then I’d give* you everything....
  -> Classifications: ['Commas']

[8/416] Lesson: Practice #1, Q1
  Category: math
  Question: [[Diagram diagram-11]]

Points A, B, C, and D lie on the edge of the circle with origin O. What is t...
  -> Classifications: ['Circles', 'Missing Angles']

[9/416] Lesson: Premium Phone Math #3, Q1
  Category: math
  Question: Throckmorton has been stealing money from the horde that I have hidden under my bed. He’s stealing i...
  -> No classifications matched

[10/416] Lesson: Function, Tone, and Phrasing, Q1
  Category: writing
  Question: Even though I've read King Lear a dozen times and seen it performed four times, Cordelia's death is ...
  -> Classifications: ['Function, Tone, and Phrasing']

[11/416] Lesson: Parentheses and Dashes, Q1
  Category: writing
  Question: The cup (which I had just filled to the brim with *water) tipped* over onto my laptop....
  -> Classifications: ['Dashes and Parentheses', 'Insertions, Deletions, and Revisions']

[12/416] Lesson: Quadratic Formula, Q1
  Category: math
  Question: y = 4x² - 2x - 3 Which of the following options provides the solutions for this equation?...
  -> Classifications: ['Quadratic Formula', 'Quadratic Functions']

[13/416] Lesson: Five More Word Problems, Q1
  Category: math
  Question: My devious cousin Throckmorton is posted up at his local coffee shop. He’s sitting at a table set wi...
  -> Classifications: ['Word Problems']

[14/416] Lesson: Premium Word Problems #1, Q1
  Category: math
  Question: I’m buying basketballs for the recreational basketball team I coach. I have $100 to spend, and each ...
  -> Classifications: ['Word Problems', 'Proportions']

[15/416] Lesson: i, Q1
  Category: math
  Question: [[Diagram diagram-12]] Which of the following expressions is equal to the fraction above?...
  -> Classifications: ['Equations']

[16/416] Lesson: Premium Practice #1, Q1
  Category: writing
  Question: *To run* is good exercise....
  -> Classifications: ['Function, Tone, and Phrasing', 'Verbs']

[17/416] Lesson: Style Practice Questions, Q1
  Category: writing
  Question: The writer is thinking about adding the following sentence: Didion was raised in Sacramento, a city ...
  -> Classifications: ['Insertions, Deletions, and Revisions', 'Function, Tone, and Phrasing']

[18/416] Lesson: Verb Practice, Q1
  Category: writing
  Question: Yesterday, Throckmorton *tries* to convince them that he didn’t eat all of their donuts....
  -> Classifications: ['Verbs']

[19/416] Lesson: Triangles, Q1
  Category: math
  Question: [[Diagram diagram-1]] ∠a is congruent to ∠d, and ∠c is congruent to ∠f. What is side length x?...
  -> Classifications: ['Triangles', 'Proportions']

[20/416] Lesson: Grammar Practice #2, Q1
  Category: writing
  Question: *Throckmorton and me* might never let go of our grudge....
  -> Classifications: ['Pronouns']

[21/416] Lesson: Phone Math #1, Q1
  Category: math
  Question: My bewildering cousin Throckmorton is digging a hole in his backyard. No one knows why. His progress...
  -> Classifications: ['Fun with Functions']

[22/416] Lesson: Colons, Q1
  Category: writing
  Question: Suddenly, I dropped my books in horror: I’d forgotten my project at home....
  -> Classifications: ['Colons']

[23/416] Lesson: Premium Practice #3, Q1
  Category: math
  Question: [[Diagram diagram-15]] What does x equal?...
  -> No classifications matched

[24/416] Lesson: Five Word Problems, Q1
  Category: math
  Question: Upfish is in the process of raising his GPA. In his efforts, he’s realized that he improves a certai...
  -> Classifications: ['Fun with Functions', 'Linear Equations']

[25/416] Lesson: Premium Grammar Practice #3, Q1
  Category: writing
  Question: I don’t like sand. It’s coarse, rough, and irritating. Which of the following is NOT an appropriate ...
  -> Classifications: ['Combining Sentences']

[26/416] Lesson: Word Problems, Q1
  Category: math
  Question: The Science Department just received a shipment of frogs that it’s going to use in dissections later...
  -> Classifications: ['Equations', 'Word Problems']

[27/416] Lesson: Premium Practice #2, Q1
  Category: math
  Question: [[Diagram diagram-7]] There are 20 boys and 20 girls on the cross country team. One of them is going...
  -> Classifications: ['Probabilities']

[28/416] Lesson: Commas, Q1
  Category: writing
  Question: *I did my laundry made my bed and performed my nightly breathing exercises.*...
  -> Classifications: ['Commas']

[29/416] Lesson: Combining Sentences, Q1
  Category: writing
  Question: Nikola Jokic is one of my favorite basketball players. He is also known as “The Joker.” What’s the m...
  -> Classifications: ['Combining Sentences']

[30/416] Lesson: Stats, Q1
  Category: math
  Question: The Cool Chair Company is testing a new lumbar support system. They invite 300 people suffering from...
  -> No classifications matched

[31/416] Lesson: Grammar Practice #1, Q1
  Category: writing
  Question: Everyone needs to make sure that *they are* in class on time tomorrow....
  -> Classifications: ['Pronouns']

[32/416] Lesson: Lightning Round, Q1
  Category: writing
  Question: If I don’t make these free throws, *then/than* we lose....
  -> Classifications: ['Function, Tone, and Phrasing']

[33/416] Lesson: Premium Practice #1, Q1
  Category: math
  Question: I’ve eaten two meatball subs in the last ten days. If I were able to keep consuming meatball subs at...
  -> Classifications: ['Word Problems']

[34/416] Lesson: Fun with Functions, Q1
  Category: math
  Question: f(x) = x²  g(x) = 2x + 3 What is f(g(b))?...
  -> Classifications: ['Fun with Functions']

[35/416] Lesson: Lines!, Q1
  Category: math
  Question: Line k crosses the y axis at 2 and contains the point (1, 0). What is the slope of this line?...
  -> Classifications: ['Linear Equations']

[36/416] Lesson: Who vs. Whom, Q1
  Category: writing
  Question: ____ got detention for the Post-It note prank?...
  -> Classifications: ['Who vs. Whom']

[37/416] Lesson: Systems of Equations, Q1
  Category: math
  Question: y = 8x + 1 This line shares intersections with all of the following options EXCEPT:...
  -> Classifications: ['Linear Equations', 'Systems of Equations']

[38/416] Lesson: The Waves, Q1
  Category: writing
  Question: *To the Lighthouse,* have become classics of the form....
  -> Classifications: ['Dashes and Parentheses']

[39/416] Lesson: Premium Word Problems #3, Q1
  Category: math
  Question: The principal of Lake River High School is debating whether or not to start construction on an addit...
  -> Classifications: ['Fun with Functions', 'Linear Equations']

[40/416] Lesson: Phone Math #2, Q1
  Category: math
  Question: Upfish gets a weekly allowance and a bonus for every test he gets an A on. His weekly income can be ...
  -> Classifications: ['Equations', 'Fun with Functions']

[41/416] Lesson: Practice #1, Q1
  Category: math
  Question: |x - y| = 5
 Which of the following is necessarily true?...
  -> Classifications: ['Inequalities', 'Word Problems']

[42/416] Lesson: Factoring Practice, Q1
  Category: math
  Question: y = x² + 6x + 8
 Which of the following is a factor of the given function?...
  -> Classifications: ['Factoring Practice', 'Quadratic Functions']

[43/416] Lesson: Moving Sentences, Q1
  Category: writing
  Question: [1] Shakespeare started his career writing mostly comedies and histories. [2] At the end of his writ...
  -> No classifications matched

[44/416] Lesson: Pronouns, Q1
  Category: writing
  Question: ___ never want to be the first person to call for the end of a water balloon war....
  -> Classifications: ['Pronouns']

[45/416] Lesson: Practice #2, Q1
  Category: math
  Question: The solutions of a quadratic equation are x = -1, and x = 5. What is the equation?...
  -> Classifications: ['Quadratic Functions', 'Factoring Practice']

[46/416] Lesson: Premium Word Problems #2, Q1
  Category: math
  Question: Erliss sells refrigerators. She’s paid a flat weekly rate plus commissions on the refrigerators she ...
  -> Classifications: ['Equations', 'Word Problems']

[47/416] Lesson: Practice #2, Q1
  Category: math
  Question:  sin ∠C = cos ∠D If ∠D = 33°, what does ∠C equal?...
  -> Classifications: ['Missing Angles', 'Triangles']

[48/416] Lesson: Equations, Q1
  Category: math
  Question: 43 = 6x - 5...
  -> Classifications: ['Linear Equations']

[49/416] Lesson: Practice #2, Q1
  Category: math
  Question: I can run one lap around a 400 meter track in 68 seconds. Assuming I’m able to maintain the same pac...
  -> Classifications: ['Word Problems']

[50/416] Lesson: Surprising Singularity, Q1
  Category: writing
  Question: What should the verb be? The US Senate *vote/votes* on Tuesday....
  -> Classifications: ['Verbs']

[51/416] Lesson: Premium Grammar Practice #2, Q1
  Category: writing
  Question: The nurses didn’t know who stole *there babie’s* candy....
  -> Classifications: ['Problematic Possessives']

[52/416] Lesson: Quadratic Functions, Q1
  Category: math
  Question: y = x² + 3x - 18  Which of the following options is a solution to the equation?...
  -> Classifications: ['Quadratic Functions', 'Equations']

[53/416] Lesson: Practice #1, Q1
  Category: math
  Question: My basketball coach is upset about how much effort we displayed in our most recent loss, so she’s ha...
  -> Classifications: ['Word Problems']

[54/416] Lesson: Premium Phone Math #1, Q1
  Category: math
  Question: Upfish is competing in a Read-a-thon. He’s already read 31 books and he can read two books per week....
  -> Classifications: ['Linear Equations', 'Word Problems']

[55/416] Lesson: Exponential Growth and Decay, Q1
  Category: math
  Question: The population of bunnies that live in the woods behind my house is plotted below. The x-axis repres...
  -> Classifications: ['Exponential Growth and Decay', 'Word Problems']

[56/416] Lesson: Mean, Median, Mode, and Range, Q1
  Category: math
  Question: Maya was sick for the game against Ville du Lac. Which of the following measures would change the mo...
  -> Classifications: ['Stats']

[57/416] Lesson: Quick Practice #1, Q1
  Category: writing
  Question: *Whom* did Throckmorton steal the rabbits from?...
  -> Classifications: ['Who vs. Whom']

[58/416] Lesson: Premium Practice #1, Q1
  Category: math
  Question: [[Diagram diagram-12]]...
  -> Classifications: ['Missing Angles']

[59/416] Lesson: Semicolons, Q1
  Category: writing
  Question: We won_ they lost....
  -> Classifications: ['Semicolons']

[60/416] Lesson: 3D Shapes, Q1
  Category: math
  Question:  The formula for the volume of a cone is [[Diagram diagram-6]]  The formula for the volume of a cyli...
  -> Classifications: ['3D shapes', 'Word Problems']

[61/416] Lesson: Quick Practice #2, Q1
  Category: writing
  Question: *Who’s* minions?...
  -> Classifications: ['Problematic Possessives']

[62/416] Lesson: Quick Practice #2, Q1
  Category: writing
  Question: I ran to the exit, *climbing* down the stairs, and jumped to safety....
  -> Classifications: ['Parallel Structure']

[63/416] Lesson: The Undead Merchant of Death, Q1
  Category: writing
  Question: Nobel was born in Sweden and was the son *of, famous inventor,* Immanuel Nobel....
  -> Classifications: ['Commas']

[64/416] Lesson: Premium Practice #1, Q1
  Category: math
  Question: |2 - x| = 1

 Which of the following is a possible value for x?...
  -> Classifications: ['Equations', 'Inequalities']

[65/416] Lesson: Practice #3, Q1
  Category: math
  Question: [[Diagram diagram-14]] What does 5b equal?...
  -> No classifications matched

[66/416] Lesson: Circles, Q1
  Category: math
  Question: My perfidious cousin Throckmorton cut himself an unreasonably large slice of pizza. The crust on his...
  -> Classifications: ['Circles', 'Word Problems']

[67/416] Lesson: Proportions, Q1
  Category: math
  Question: Erliss is stuck in traffic on her way to work. She moved only 2 miles in the last 24 minutes. At thi...
  -> Classifications: ['Word Problems', 'Proportions']

[68/416] Lesson: My Belovèd Hoodie, Q1
  Category: writing
  Question: I’ve never cared much [1] in fashion....
  -> Classifications: ['Function, Tone, and Phrasing']

[69/416] Lesson: Transitional Expressions, Q1
  Category: writing
  Question: I wanted to go for a jog. _____, it started to rain, so I couldn’t....
  -> Classifications: ['Transitional Expressions']

[70/416] Lesson: Phone Math #3, Q1
  Category: math
  Question: The population of rabbits at my house is shooting up. Which of the following could be the graph of t...
  -> No classifications matched

[71/416] Lesson: Weird Verbs, Q1
  Category: writing
  Question: Saw that she got into her dream college, Erliss jumped up, ran around excitedly, and threw all of he...
  -> Classifications: ['Verbs']

[72/416] Lesson: Grammar Practice #3, Q1
  Category: writing
  Question: I may be the star quarterback on the football *team, but* my real dream is to be a ballet dancer!...
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[73/416] Lesson: Verbs, Q1
  Category: writing
  Question: The students, one of whom is throwing his lunch at the others, ____ getting restless....
  -> Classifications: ['Pronouns', 'Verbs']

[74/416] Lesson: Missing Angles, Q1
  Category: math
  Question: [[Diagram diagram-8]] v = ?...
  -> Classifications: ['Missing Angles']

[75/416] Lesson: Probabilities, Q1
  Category: math
  Question: If an evening is chosen at random, what is the likelihood that Upfish didn’t have any homework to do...
  -> Classifications: ['Probabilities']

[76/416] Lesson: The Mexican Phoenix, Q1
  Category: writing
  Question: Born in Mexico in 1651, her parents were a Spanish Captain and a Creole woman to whom she was an ill...
  -> Classifications: ['Misplaced Modifiers']

[77/416] Lesson: Problematic Possessives, Q1
  Category: writing
  Question: I don’t know ____ leaving me all of these prank voicemail messages, but they have to stop!...
  -> Classifications: ['Who vs. Whom']

[78/416] Lesson: Math Diagnostic, Q1
  Category: math
  Question: Erliss has been offered jobs at two companies. She’s debating which offer to accept. Company A would...
  -> Classifications: ['Word Problems', 'Linear Equations']

[79/416] Lesson: Murder!, Q1
  Category: writing
  Question: The widow of Leland Stanford and primary donor to Stanford University drank a lethal dose of strychn...
  -> Classifications: ['Function, Tone, and Phrasing']

[80/416] Lesson: Parallel Structure, Q1
  Category: writing
  Question: Last year, I was elected junior class president, served on the homecoming committee, and played on t...
  -> Classifications: ['Combining Sentences', 'Parallel Structure']

[81/416] Lesson: Premium Practice #4, Q1
  Category: math
  Question: [[Diagram diagram-1]] What is one solution for c?...
  -> No classifications matched

[82/416] Lesson: Premium Practice #2, Q1
  Category: writing
  Question: Somebody *know* more than they’re saying....
  -> Classifications: ['Surprising Singularity', 'Verbs']

[83/416] Lesson: Premium Phone Math #2, Q1
  Category: math
  Question: It’s five miles from my house to the stadium, which is due east of me. It’s twelve miles from the st...
  -> Classifications: ['Triangles', 'Word Problems']

[84/416] Lesson: Inequalities, Q1
  Category: math
  Question: My perfidious cousin Throckmorton is trying to amass at least $50 for a new scooter. He could buy a ...
  -> Classifications: ['Inequalities', 'Word Problems', 'Linear Equations']

[85/416] Lesson: Practice #4, Q1
  Category: math
  Question: [[Diagram diagram-12]]What is one solution for b?...
  -> No classifications matched

[86/416] Lesson: Insertions, Deletions, and Revisions, Q1
  Category: writing
  Question: My mom goes on a [1] daily bike ride every single day. She has a few preferred trails. She finds the...
  -> Classifications: ['Insertions, Deletions, and Revisions']

[87/416] Lesson: Premium Practice #2, Q1
  Category: math
  Question: [[Diagram diagram-2]]

What is the length of EC?...
  -> Classifications: ['Triangles', 'Proportions', 'Word Problems']

[88/416] Lesson: Misplaced Modifiers, Q1
  Category: writing
  Question: *Hungrily barking, Odysseus fed his dog.*...
  -> Classifications: ['Misplaced Modifiers']

[89/416] Lesson: Exponents, Q1
  Category: math
  Question: x²(x⁴ - x) = ?...
  -> Classifications: ['Exponents and Radicals', 'Factoring Practice']

[90/416] Lesson: Premium Practice #2, Q2
  Category: math
  Question: In the past ten years, the price of a bag of my favorite type of chip has increased 25%. It’s curren...
  -> Classifications: ['Word Problems', 'Proportions']

[91/416] Lesson: Premium Word Problems #2, Q2
  Category: math
  Question: I like two types of pen: medium-sized soft feel and cristal 1.6mm. A box of medium-sized soft feels,...
  -> Classifications: ['Inequalities', 'Word Problems']

[92/416] Lesson: Surprising Singularity, Q2
  Category: writing
  Question: The room of 200 incoming freshmen *is/are* falling asleep during the Vice Principal's remarks....
  -> Classifications: ['Verbs']

[93/416] Lesson: Premium Practice #1, Q2
  Category: math
  Question: Every time I eat a meatball sandwich, my cousin Throckmorton steals a bite or two. During our previo...
  -> Classifications: ['Word Problems']

[94/416] Lesson: Practice #3, Q2
  Category: math
  Question: a + b = 4
 a - b = 8
 What is the value of ab?...
  -> Classifications: ['Systems of Equations', 'Linear Equations']

[95/416] Lesson: Misplaced Modifiers, Q2
  Category: writing
  Question: *On the way back from school, a pot of gold was found.*...
  -> Classifications: ['Moving Sentences']

[96/416] Lesson: Premium Practice #2, Q2
  Category: writing
  Question: The two *teams’* buses collided....
  -> Classifications: ['Problematic Possessives']

[97/416] Lesson: Semicolons, Q2
  Category: writing
  Question: While the security guards tried to hold the fans back_ they poured onto the court to celebrate....
  -> Classifications: ['Commas']

[98/416] Lesson: Equations, Q2
  Category: math
  Question: |x - 3| + 1...
  -> Classifications: ['Inequalities', 'Fun with Functions']

[99/416] Lesson: Premium Practice #1, Q2
  Category: writing
  Question: Erliss— who just happened to fly into New York from Norway on Thanksgiving *Day) thought* that Ameri...
  -> Classifications: ['Dashes and Parentheses']

[100/416] Lesson: Premium Phone Math #3, Q2
  Category: math
  Question: [[Diagram diagram-2]] Which point shows the moment when I run out of money in my horde?...
  -> No classifications matched

[101/416] Lesson: Circles, Q2
  Category: math
  Question: A 120° arc is equivalent to how many radians?...
  -> Classifications: ['Circles']

[102/416] Lesson: Systems of Equations, Q2
  Category: math
  Question: Upfish’s parents reward him for doing well in school by giving him $5 for every A he gets, but they ...
  -> Classifications: ['Word Problems', 'Systems of Equations']

[103/416] Lesson: Grammar Practice #1, Q2
  Category: writing
  Question: The members of the senior class who covered the Principal’s car in Post-it notes and pulled the fire...
  -> Classifications: ['Combining Sentences', 'Misplaced Modifiers']

[104/416] Lesson: Insertions, Deletions, and Revisions, Q2
  Category: writing
  Question: My mom goes on a bike ride every single day. [2] She has a few preferred trails. She finds the waves...
  -> No classifications matched

[105/416] Lesson: Function, Tone, and Phrasing, Q2
  Category: writing
  Question: The looming threat of war convinced the two Heads of State to finally come together for a diplomatic...
  -> No classifications matched

[106/416] Lesson: Phone Math #2, Q2
  Category: math
  Question: I want to try something: I want to make a pizza and top it with one, single pepperoni that goes over...
  -> Classifications: ['Circles']

[107/416] Lesson: Premium Practice #4, Q2
  Category: math
  Question: y = 14x² + 49x - 21 Which of the following is a solution for x?...
  -> No classifications matched

[108/416] Lesson: Style Practice Questions, Q2
  Category: writing
  Question: A) NO CHANGE
B) since he was the author of several novels.
C) as he was a writer too
D) DELETE the u...
  -> Classifications: ['Insertions, Deletions, and Revisions']

[109/416] Lesson: Problematic Possessives, Q2
  Category: writing
  Question: The weather doesn’t seem to be able to make up ___ mind today....
  -> Classifications: ['Problematic Possessives']

[110/416] Lesson: Exponential Growth and Decay, Q2
  Category: math
  Question: Which of the following represents exponential decay?...
  -> Classifications: ['Exponential Growth and Decay']

[111/416] Lesson: Practice #2, Q2
  Category: math
  Question: On his first three Spanish tests of the semester, Upfish scored 95, 85, and 90. He scored exactly 90...
  -> No classifications matched

[112/416] Lesson: Premium Grammar Practice #1, Q2
  Category: writing
  Question: The *teachers’ students* threw them a surprise party....
  -> Classifications: ['Problematic Possessives']

[113/416] Lesson: Math Diagnostic, Q2
  Category: math
  Question: [[Diagram diagram-17]] What is the y-intercept of the line above?...
  -> Classifications: ['Linear Equations']

[114/416] Lesson: Premium Grammar Practice #3, Q2
  Category: writing
  Question: Be on the lookout for Pythagorean triples, especially the triangle with sides of 3, 4, and *a side o...
  -> Classifications: ['Insertions, Deletions, and Revisions']

[115/416] Lesson: Premium Practice #2, Q2
  Category: math
  Question: The following frequency charts give the distribution of different scores on two recent unit tests.  ...
  -> Classifications: ['Stats']

[116/416] Lesson: Premium Practice #2, Q2
  Category: math
  Question: [[Diagram diagram-3]]

The cosine of ∠f is 0.28. What is the sine of ∠e?...
  -> Classifications: ['Triangles']

[117/416] Lesson: Factoring Practice, Q2
  Category: math
  Question: y = x² - 7x + 10
 Which of the following is a factor of the given function?...
  -> Classifications: ['Factoring Practice', 'Quadratic Functions']

[118/416] Lesson: The Undead Merchant of Death, Q2
  Category: writing
  Question: Alfred made a fortune investing in oil refineries and held 355 *patents, however,* he was most well-...
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[119/416] Lesson: Practice #4, Q2
  Category: math
  Question: y = 4x³ + 20x² + 8x  What are the nonzero solutions to the equation?...
  -> Classifications: ['Equations', 'Fun with Functions']

[120/416] Lesson: Probabilities, Q2
  Category: math
  Question: If an evening is chosen at random, what’s the chance that Upfish completed one or three hours of hom...
  -> Classifications: ['Probabilities']

[121/416] Lesson: Stats, Q2
  Category: math
  Question: Upfish usually does very well on his math tests. Before his last test, he’d scored at least a 92 on ...
  -> Classifications: ['Stats']

[122/416] Lesson: Phone Math #1, Q2
  Category: math
  Question: Your history teacher just finished grading your last test. She suspects that the students with the t...
  -> Classifications: ['Stats']

[123/416] Lesson: Premium Word Problems #3, Q2
  Category: math
  Question: Tickets to the school play are $5 for students and $10 for the general public. The Theater Club will...
  -> Classifications: ['Inequalities', 'Word Problems']

[124/416] Lesson: Phone Math #3, Q2
  Category: math
  Question: [[Diagram diagram-2]] Which point indicates the number of rabbits I bought to begin with?...
  -> Classifications: ['Word Problems', 'Fun with Functions']

[125/416] Lesson: Quick Practice #2, Q2
  Category: writing
  Question: *Failing to get it back on its leash, Upfish’s peacock ran free.*...
  -> Classifications: ['Misplaced Modifiers']

[126/416] Lesson: Word Problems, Q2
  Category: math
  Question: Your homeroom takes the annual canned food drive contest very seriously. There are 25 students in yo...
  -> Classifications: ['Word Problems']

[127/416] Lesson: Five Word Problems, Q2
  Category: math
  Question: I want to keep track of how many donuts I eat this year. I’ve been eating my feelings a lot lately, ...
  -> Classifications: ['Equations', 'Word Problems']

[128/416] Lesson: Premium Grammar Practice #2, Q2
  Category: writing
  Question: The secret, passed down by countless generations through centuries and centuries, *are* to put one’s...
  -> Classifications: ['Verbs']

[129/416] Lesson: Practice #1, Q2
  Category: math
  Question: In all, practice ran from 3 to 4:15 pm. What percentage of my total lap count did I complete between...
  -> No classifications matched

[130/416] Lesson: Murder!, Q2
  Category: writing
  Question: [2] *Whom* did it?...
  -> Classifications: ['Who vs. Whom']

[131/416] Lesson: Grammar Practice #3, Q2
  Category: writing
  Question: *She nevertheless, poured* an entire vial of glitter on his head....
  -> Classifications: ['Transitional Expressions']

[132/416] Lesson: Combining Sentences, Q2
  Category: writing
  Question: Homer had a short-lived job voicing Poochy the Dog. This character was one of the most loathed late-...
  -> Classifications: ['Combining Sentences']

[133/416] Lesson: Quadratic Formula, Q2
  Category: math
  Question: y = 2x² + 4x + 6 How many real solutions are there for the given equation?...
  -> Classifications: ['Quadratic Formula', 'Quadratic Functions']

[134/416] Lesson: Premium Practice #1, Q2
  Category: math
  Question: [[Diagram diagram-15]]

What’s x?...
  -> Classifications: ['Missing Angles', 'Triangles']

[135/416] Lesson: Pronouns, Q2
  Category: writing
  Question: Throckmorton retaliated against Clarice and ____....
  -> Classifications: ['Pronouns']

[136/416] Lesson: The Waves, Q2
  Category: writing
  Question: It’s so experimental that Woolf invented a new term to describe this *work: “playpoem.”*...
  -> Classifications: ['Colons']

[137/416] Lesson: Who vs. Whom, Q2
  Category: writing
  Question: ____ did the principal call into her office for questioning?...
  -> Classifications: ['Who vs. Whom']

[138/416] Lesson: Five More Word Problems, Q2
  Category: math
  Question: I like to listen to lofi hip hop beat tapes while I write these questions. My favorite producer publ...
  -> Classifications: ['Word Problems']

[139/416] Lesson: Lightning Round, Q2
  Category: writing
  Question: There was *fewer/less* enthusiasm for the election than ever....
  -> Classifications: ['Problematic Possessives']

[140/416] Lesson: Radicals, Q2
  Category: math
  Question: What is the most simplified form of ?...
  -> No classifications matched

[141/416] Lesson: Premium Word Problems #1, Q2
  Category: math
  Question: At her old company, Erliss was paid $500 a week plus a 20% commission on all her sales. At her new c...
  -> Classifications: ['Inequalities', 'Word Problems']

[142/416] Lesson: Parallel Structure, Q2
  Category: writing
  Question: My dad asked me to take out the trash, do the dishes, clean my room, and my homework....
  -> Classifications: ['Parallel Structure']

[143/416] Lesson: Quick Practice #1, Q2
  Category: writing
  Question: Before Lauren called and told me about the rabbit robbery, I *had never thought* my duplicitous cous...
  -> Classifications: ['Verbs']

[144/416] Lesson: Verb Practice, Q2
  Category: writing
  Question: You *are talking* about maybe 6% of the vote here....
  -> Classifications: ['Verbs']

[145/416] Lesson: Practice #2, Q2
  Category: math
  Question: Which of the following is the equation of a circle which contains the point (-1, 2) and has its cent...
  -> Classifications: ['Circles']

[146/416] Lesson: Practice #1, Q2
  Category: math
  Question: 5x(x + 2) - (2x² + 7) = ?...
  -> Classifications: ['Equations', 'Factoring Practice']

[147/416] Lesson: Verbs, Q2
  Category: writing
  Question: Sir John Falstaff— out of all of the heroes and villains in all of the histories, tragedies, comedie...
  -> Classifications: ['Verbs']

[148/416] Lesson: Practice #2, Q2
  Category: math
  Question: They say that everything is 15% more expensive in big cities. If a gallon of milk costs $3 in the ma...
  -> Classifications: ['Word Problems', 'Proportions']

[149/416] Lesson: The Mexican Phoenix, Q2
  Category: writing
  Question: Which of the following options presents the most effective description?...
  -> Classifications: ['Function, Tone, and Phrasing', 'Insertions, Deletions, and Revisions']

[150/416] Lesson: Premium Practice #3, Q2
  Category: math
  Question: [[Diagram diagram-2]] Which option models the relation between f(x) and x?...
  -> Classifications: ['Fun with Functions']

[151/416] Lesson: Premium Practice #1, Q2
  Category: math
  Question: (3x + 7) - (2x - 1) = ?...
  -> Classifications: ['Equations']

[152/416] Lesson: Transitional Expressions, Q2
  Category: writing
  Question: She’s getting better and better at free throws. _____, she had only made about half of them. Now, sh...
  -> Classifications: ['Transitional Expressions']

[153/416] Lesson: Lines!, Q2
  Category: math
  Question: Every week of the semester, I get less and less sleep. At the beginning of the semester, I got 8 hou...
  -> Classifications: ['Fun with Functions', 'Linear Equations', 'Word Problems']

[154/416] Lesson: Premium Practice #2, Q2
  Category: writing
  Question: I ate some popcorn, drank a soda, and *had been watching* a movie....
  -> Classifications: ['Parallel Structure']

[155/416] Lesson: Premium Phone Math #1, Q2
  Category: math
  Question: My tyrannical cousin Throckmorton is recruiting minions again. He successfully recruits three minion...
  -> Classifications: ['Exponential Growth and Decay']

[156/416] Lesson: Grammar Practice #2, Q2
  Category: writing
  Question: The students *whom* want to try out for the play should sign up for an audition slot....
  -> Classifications: ['Who vs. Whom']

[157/416] Lesson: Exponents, Q2
  Category: math
  Question: If 2ᵃ = b, what does 4ᵃ/b equal?...
  -> Classifications: ['Exponents and Radicals', 'Fun with Functions']

[158/416] Lesson: Introductions, Transitions, and Conclusions, Q2
  Category: writing
  Question: Which of the following provides the best transition from the preceding paragraph to the one that fol...
  -> Classifications: ['Introductions, Transitions, and Conclusions']

[159/416] Lesson: Missing Angles, Q2
  Category: math
  Question: [[Diagram diagram-19]] What does z equal?...
  -> Classifications: ['Missing Angles', 'Triangles']

[160/416] Lesson: Quadratic Functions, Q2
  Category: math
  Question: y = x² + 2x - 8  Which of the following is the vertex of the given equation?...
  -> Classifications: ['Quadratic Functions']

[161/416] Lesson: Parentheses and Dashes, Q2
  Category: writing
  Question: Surprisingly, my computer still worked after I dried it *off though— I* couldn’t use the left half o...
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[162/416] Lesson: Practice #1, Q2
  Category: math
  Question: [[Diagram diagram-16]]

UV || RS and angle measures are as marked. What is x?...
  -> Classifications: ['Missing Angles']

[163/416] Lesson: My Belovèd Hoodie, Q2
  Category: writing
  Question: I’d rather be comfortable [2] then look good relative to some arbitrary, ever-changing definition of...
  -> Classifications: ['Problematic Possessives']

[164/416] Lesson: Colons, Q2
  Category: writing
  Question: I only had one thing left in my refrigerator. A rotting red onion....
  -> Classifications: ['Colons']

[165/416] Lesson: Premium Practice #1, Q2
  Category: writing
  Question: They don’t know *there* way around....
  -> Classifications: ['Problematic Possessives']

[166/416] Lesson: Quick Practice #2, Q2
  Category: writing
  Question: The door opened. It was Upfish! Which of the following is NOT an appropriate way to combine these tw...
  -> Classifications: ['Combining Sentences']

[167/416] Lesson: Premium Phone Math #2, Q2
  Category: math
  Question: The ghosts that are haunting me keep inviting more ghosts to join in the haunting every night. The f...
  -> Classifications: ['Exponential Growth and Decay', 'Fun with Functions']

[168/416] Lesson: Weird Verbs, Q2
  Category: writing
  Question: I reached into the box only to realize that someone had eaten the last of the donuts....
  -> No classifications matched

[169/416] Lesson: Quick Practice #1, Q2
  Category: writing
  Question: I’d take your *dreams and make* them multiply....
  -> Classifications: ['Commas']

[170/416] Lesson: Commas, Q2
  Category: writing
  Question: Although I didn't know *how to get there I was too* proud to ask for directions....
  -> Classifications: ['Commas', 'Introductions, Transitions, and Conclusions']

[171/416] Lesson: Practice #3, Q3
  Category: math
  Question: [[Diagram diagram-10]] What does C equal?...
  -> No classifications matched

[172/416] Lesson: Quick Practice #2, Q3
  Category: writing
  Question: You and *me* are in this together....
  -> Classifications: ['Pronouns']

[173/416] Lesson: Colons, Q3
  Category: writing
  Question: I really enjoy a few of Virginia Woolf’s less widely-discussed books, such as: The Waves, Between th...
  -> Classifications: ['Colons', 'Insertions, Deletions, and Revisions']

[174/416] Lesson: Premium Practice #2, Q3
  Category: writing
  Question: *Sitting on a fence, a wind blew Upfish over.*...
  -> Classifications: ['Misplaced Modifiers', 'Insertions, Deletions, and Revisions']

[175/416] Lesson: Equations, Q3
  Category: math
  Question: When five is added to a number, the result is seven less than 15. What is the number?...
  -> Classifications: ['Word Problems', 'Linear Equations']

[176/416] Lesson: Problematic Possessives, Q3
  Category: writing
  Question: ____ good dogs, Brent....
  -> Classifications: ['Pronouns']

[177/416] Lesson: Premium Practice #4, Q3
  Category: math
  Question: y < x < 2y  Which of the following statements about x and y is true?...
  -> Classifications: ['Inequalities']

[178/416] Lesson: Premium Practice #2, Q3
  Category: math
  Question: Questions 3,4, and 5 use the same graph.  Below is a graph relating my 400m dash times to the amount...
  -> Classifications: ['Fun with Functions', 'Word Problems']

[179/416] Lesson: Practice #1, Q3
  Category: math
  Question: 2y + 10x = 4
 
Which of the following lines is perpendicular to the line given?...
  -> Classifications: ['Linear Equations', 'Fun with Functions']

[180/416] Lesson: My Belovèd Hoodie, Q3
  Category: writing
  Question: Nonetheless, my all-time favorite article of clothing was a ratty, old hooded sweatshirt that was wo...
  -> Classifications: ['Colons']

[181/416] Lesson: Practice #4, Q3
  Category: math
  Question: My Pokemon card collection increases in value by 15% every ten years. Currently, it’s worth $2000. H...
  -> Classifications: ['Exponential Growth and Decay', 'Word Problems']

[182/416] Lesson: Premium Phone Math #1, Q3
  Category: math
  Question: Erliss is trying to measure how far she goes when she rides her bike to the quarry she likes to swim...
  -> Classifications: ['Circles']

[183/416] Lesson: Premium Grammar Practice #1, Q3
  Category: writing
  Question: *Who’s* house is the meeting taking place at?...
  -> Classifications: ['Problematic Possessives']

[184/416] Lesson: Exponential Growth and Decay, Q3
  Category: math
  Question: Every time I do laundry, I lose 10% of my socks. Every time. I do laundry twice a month. If I have 2...
  -> Classifications: ['Exponential Growth and Decay', 'Word Problems']

[185/416] Lesson: Misplaced Modifiers, Q3
  Category: writing
  Question: *After spending more than twenty years in school, Janet’s medical degree was well-deserved.*...
  -> Classifications: ['Misplaced Modifiers', 'Insertions, Deletions, and Revisions']

[186/416] Lesson: Quick Practice #2, Q3
  Category: writing
  Question: I am once *again asking for* your financial support....
  -> No classifications matched

[187/416] Lesson: Commas, Q3
  Category: writing
  Question: *My car, which has a leaky gas tank, ran out of fuel.*...
  -> Classifications: ['Commas']

[188/416] Lesson: The Waves, Q3
  Category: writing
  Question: The best placement for sentence E is:...
  -> Classifications: ['Moving Sentences']

[189/416] Lesson: Premium Word Problems #3, Q3
  Category: math
  Question: I accidentally ordered a 12 foot sub when I wanted a 12 inch sub. I ate as much as I could in one si...
  -> Classifications: ['Word Problems']

[190/416] Lesson: Quadratic Functions, Q3
  Category: math
  Question: y = 3(x + 2)(x + j)  The vertex of this equation is (-1, -3). What is j?...
  -> Classifications: ['Fun with Functions', 'Quadratic Functions']

[191/416] Lesson: Style Practice Questions, Q3
  Category: writing
  Question: A) NO CHANGE
B) was much-discussed when it came out.
C) was very well-received.
D) won the National ...
  -> No classifications matched

[192/416] Lesson: Phone Math #2, Q3
  Category: math
  Question: I like the color blue, and I like the way the color blue looks on me. I’ve been told, however, that ...
  -> Classifications: ['Inequalities', 'Word Problems']

[193/416] Lesson: Premium Practice #1, Q3
  Category: math
  Question: Which of the following graphs exhibits a strong negative association between x and y?...
  -> Classifications: ['Stats']

[194/416] Lesson: Five Word Problems, Q3
  Category: math
  Question: Your English class is competing in a Read-a-thon. Your class has read 57 books so far. On average, 3...
  -> Classifications: ['Word Problems']

[195/416] Lesson: Premium Phone Math #3, Q3
  Category: math
  Question: Here’s a chart of the clothes hanging in my closet sorted by color. [[Diagram diagram-1]] If I pick ...
  -> Classifications: ['Probabilities']

[196/416] Lesson: The Undead Merchant of Death, Q3
  Category: writing
  Question: Furthermore, while he was a pacifist himself, his *families* business ran about 100 armaments facili...
  -> Classifications: ['Problematic Possessives']

[197/416] Lesson: Premium Practice #2, Q3
  Category: math
  Question: The slope of line k is undefined. Line k travels through two quadrants in the (x, y) coordinate plan...
  -> Classifications: ['Linear Equations']

[198/416] Lesson: Premium Word Problems #1, Q3
  Category: math
  Question: During our last water balloon fight, my cousin Throckmorton and I threw a combined total of 132 ball...
  -> Classifications: ['Word Problems']

[199/416] Lesson: Practice #2, Q3
  Category: math
  Question: Questions 3, 4, and 5 refer to the following information. 

 The graph below plots the amount of tim...
  -> Classifications: ['Fun with Functions', 'Stats', 'Word Problems']

[200/416] Lesson: Practice #2, Q3
  Category: math
  Question: A line graphed on the (x, y) coordinate plane contains points in quadrants I, III, and IV. However, ...
  -> Classifications: ['Linear Equations']

[201/416] Lesson: Probabilities, Q3
  Category: math
  Question: Of the evenings on which Upfish had less than three hours of homework, how many started with the let...
  -> Classifications: ['Probabilities']

[202/416] Lesson: Quick Practice #1, Q3
  Category: writing
  Question: *Seeing* that the rabbit hutch was empty....
  -> Classifications: ['Verbs']

[203/416] Lesson: Premium Practice #1, Q3
  Category: math
  Question: [[Diagram diagram-4]]

What’s x?...
  -> Classifications: ['Triangles', 'Missing Angles']

[204/416] Lesson: Factoring Practice, Q3
  Category: math
  Question: y = x² + x - 20
 Which of the following is a factor of the given function?...
  -> Classifications: ['Factoring Practice', 'Quadratic Functions']

[205/416] Lesson: Practice #2, Q3
  Category: math
  Question: A soda company is redesigning its cans. Originally, the cylindrical cans had a diameter of 2 inches ...
  -> Classifications: ['3D shapes', 'Word Problems']

[206/416] Lesson: Premium Practice #1, Q3
  Category: writing
  Question: The waiter added extra fries to the three *nurse’s* orders....
  -> Classifications: ['Problematic Possessives']

[207/416] Lesson: Practice #1, Q3
  Category: math
  Question: [[Diagram diagram-22]]

Line segment XY is perpendicular to WZ. What is the length of XW?...
  -> Classifications: ['Triangles', 'Word Problems']

[208/416] Lesson: Grammar Practice #3, Q3
  Category: writing
  Question: When you become a master ninja, *one is* expected to pass on what you know to the next generation....
  -> Classifications: ['Pronouns']

[209/416] Lesson: Five More Word Problems, Q3
  Category: math
  Question: Johnny has 19 bottles of dish soap. Each bottle contains 48 ounces of soap. He uses about 16 oz. of ...
  -> Classifications: ['Word Problems']

[210/416] Lesson: Practice #1, Q3
  Category: math
  Question: Which of the following graphs exhibits a positive association between x and y?...
  -> Classifications: ['Fun with Functions', 'Stats']

[211/416] Lesson: Function, Tone, and Phrasing, Q3
  Category: writing
  Question: The formaldehyde used to preserve the frogs we were about to dissect was quite *smelly*....
  -> Classifications: ['Function, Tone, and Phrasing']

[212/416] Lesson: Surprising Singularity, Q3
  Category: writing
  Question: What should the verb be? Somebody— or something—          haunting me at night....
  -> Classifications: ['Verbs']

[213/416] Lesson: Premium Practice #1, Q3
  Category: writing
  Question: She gave detention to Erliss and *I*....
  -> Classifications: ['Pronouns']

[214/416] Lesson: Math Diagnostic, Q3
  Category: math
  Question: I’ve had a tumultuous start to the basketball season. The first two games, I scored 18 points then 1...
  -> Classifications: ['Stats', 'Mean, Median, Mode, and Range']

[215/416] Lesson: Premium Practice #2, Q3
  Category: writing
  Question: Even *though, I was* trying to hide it, I was totally freaking out....
  -> Classifications: ['Combining Sentences']

[216/416] Lesson: Lightning Round, Q3
  Category: writing
  Question: The *effect/affect* of her action might not be fully appreciated for centuries....
  -> Classifications: ['Verbs']

[217/416] Lesson: Quick Practice #1, Q3
  Category: writing
  Question: My throat closed *up — I guess I* can’t eat four mangoes in one sitting)....
  -> Classifications: ['Dashes and Parentheses', 'Combining Sentences']

[218/416] Lesson: Grammar Practice #1, Q3
  Category: writing
  Question: She *knows* what she needed to do, she just didn’t do it....
  -> Classifications: ['Verbs']

[219/416] Lesson: Grammar Practice #2, Q3
  Category: writing
  Question: The cast of 40 students from each of the grades *need* to rehearse daily to get comfortable performi...
  -> Classifications: ['Surprising Singularity']

[220/416] Lesson: Semicolons, Q3
  Category: writing
  Question: The fans hoisted the star point guard on their shoulders_ he smiled ecstatically, even though he was...
  -> Classifications: ['Semicolons']

[221/416] Lesson: Circles, Q3
  Category: math
  Question: 315° = ?...
  -> No classifications matched

[222/416] Lesson: Weird Verbs, Q3
  Category: writing
  Question: Upfish got a lot faster since he started running so much....
  -> Classifications: ['Verbs']

[223/416] Lesson: Introductions, Transitions, and Conclusions, Q3
  Category: writing
  Question: Which option provides the best conclusion to the passage?...
  -> No classifications matched

[224/416] Lesson: Transitional Expressions, Q3
  Category: writing
  Question: I’m fluent in English, French, and German. _____, I’m teaching myself Spanish and Japanese....
  -> Classifications: ['Transitional Expressions']

[225/416] Lesson: Premium Practice #2, Q3
  Category: math
  Question: My tyrannical cousin Throckmorton is having his followers build him a pyramid in his honor. Original...
  -> Classifications: ['3D shapes', 'Word Problems']

[226/416] Lesson: Verb Practice, Q3
  Category: writing
  Question: I tried as hard as I could on the test, but I *will know* the results until next Monday....
  -> Classifications: ['Function, Tone, and Phrasing']

[227/416] Lesson: Insertions, Deletions, and Revisions, Q3
  Category: writing
  Question: My mom goes on a daily bike ride every single day. She has a few preferred trails. She finds the wav...
  -> Classifications: ['Insertions, Deletions, and Revisions']

[228/416] Lesson: Pronouns, Q3
  Category: writing
  Question: ___ and my little sister had been in cahoots the entire time....
  -> Classifications: ['Pronouns']

[229/416] Lesson: Lines!, Q3
  Category: math
  Question: Which of the following options is parallel to the line that contains the points (2, 0) and (0, 4)?...
  -> Classifications: ['Linear Equations']

[230/416] Lesson: Premium Word Problems #2, Q3
  Category: math
  Question: I’m training for a marathon. Currently, I can only run two miles before I faint. I can increase my s...
  -> Classifications: ['Word Problems']

[231/416] Lesson: Premium Grammar Practice #2, Q3
  Category: writing
  Question: Viola steps ashore, dresses in men’s clothing, and *goes to* work for the Duke....
  -> Classifications: ['Parallel Structure']

[232/416] Lesson: Premium Grammar Practice #3, Q3
  Category: writing
  Question: Here *are* some important information about your classes this semester....
  -> Classifications: ['Verbs']

[233/416] Lesson: Murder!, Q3
  Category: writing
  Question: Well, the most likely [3] *perp* was none other than the President of Stanford University, David Sta...
  -> No classifications matched

[234/416] Lesson: Parallel Structure, Q3
  Category: writing
  Question: I hate to admit it, but she’s a much better driver than my driving....
  -> Classifications: ['Pronouns']

[235/416] Lesson: Phone Math #1, Q3
  Category: math
  Question: I walk due west from my house to the store where I buy my protein bar on my way to basketball. Then ...
  -> Classifications: ['Triangles', 'Word Problems']

[236/416] Lesson: The Mexican Phoenix, Q3
  Category: writing
  Question: She was hugely self-taught....
  -> Classifications: ['Function, Tone, and Phrasing']

[237/416] Lesson: Premium Practice #1, Q3
  Category: math
  Question: Which of the following lines is parallel to the line with the equation y = -2x + 5?...
  -> Classifications: ['Linear Equations']

[238/416] Lesson: Premium Phone Math #2, Q3
  Category: math
  Question: In the basketball game last night, I scored the most points I’ve ever scored in a single game: 40. I...
  -> Classifications: ['Stats']

[239/416] Lesson: Phone Math #3, Q3
  Category: math
  Question: Here’s a chart of the clothes hanging in my closet sorted by color: [[Diagram diagram-1]] If I pick ...
  -> Classifications: ['Probabilities']

[240/416] Lesson: Premium Practice #3, Q3
  Category: math
  Question: x²(x - 4) = -4x In the equation above, where x > 0, what is x?...
  -> Classifications: ['Quadratic Functions', 'Equations']

[241/416] Lesson: My Belovèd Hoodie, Q4
  Category: writing
  Question: At this point, the writer is thinking of adding the following sentence: Three of my favorite basketb...
  -> No classifications matched

[242/416] Lesson: Grammar Practice #1, Q4
  Category: writing
  Question: *Driving along the pitch-black road at night, a deer jumped out of the woods.*...
  -> Classifications: ['Misplaced Modifiers']

[243/416] Lesson: Premium Practice #2, Q4
  Category: writing
  Question: Don’t ask for *who* the bell tolls....
  -> Classifications: ['Who vs. Whom', 'Pronouns']

[244/416] Lesson: Quick Practice #1, Q4
  Category: writing
  Question: Still, I ate another *mango— I like* them too much....
  -> Classifications: ['Dashes and Parentheses']

[245/416] Lesson: Verb Practice, Q4
  Category: writing
  Question: I *call* my parents to make sure it was okay before I booked the tickets....
  -> Classifications: ['Verbs']

[246/416] Lesson: Quick Practice #1, Q4
  Category: writing
  Question: Since he stole the rabbits, Throck *was teasing* them with fake carrots....
  -> Classifications: ['Verbs']

[247/416] Lesson: Premium Phone Math #2, Q4
  Category: math
  Question: If a quadratic function factors out to (x + 3)(x - 5) = 0, then what are the solutions to the functi...
  -> Classifications: ['Quadratic Functions', 'Factoring Practice']

[248/416] Lesson: Premium Word Problems #1, Q4
  Category: math
  Question: Riverlake High School is renovating its auditorium. The new addition will increase the seating capac...
  -> Classifications: ['Word Problems']

[249/416] Lesson: Premium Word Problems #2, Q4
  Category: math
  Question: I’ve been practicing my speed-reading recently. Three weeks after I started training, I could read 7...
  -> No classifications matched

[250/416] Lesson: Premium Grammar Practice #2, Q4
  Category: writing
  Question: *Hopping up and down excitedly, I caught the bunny.*...
  -> Classifications: ['Misplaced Modifiers']

[251/416] Lesson: Equations, Q4
  Category: math
  Question: What is the difference?...
  -> Classifications: ['Exponents and Radicals', 'Factoring Practice', 'Fun with Functions']

[252/416] Lesson: Practice #3, Q4
  Category: math
  Question: f(x) = ax² - 16
 If f(2) = 4, then what does f(3) equal?...
  -> Classifications: ['Quadratic Functions', 'Fun with Functions']

[253/416] Lesson: Pronouns, Q4
  Category: writing
  Question: You should never get into never-ending water balloon wars with members of your family. ___ should li...
  -> Classifications: ['Pronouns']

[254/416] Lesson: Five Word Problems, Q4
  Category: math
  Question: I’m starting a new basketball team. The league I want to join charges $460 per team. If every member...
  -> Classifications: ['Word Problems', 'Inequalities']

[255/416] Lesson: Quick Practice #2, Q4
  Category: writing
  Question: The waiter spit in each of the three *senators orders*....
  -> Classifications: ['Problematic Possessives']

[256/416] Lesson: Grammar Practice #3, Q4
  Category: writing
  Question: *Whom* did you invite to prom?...
  -> Classifications: ['Who vs. Whom']

[257/416] Lesson: The Waves, Q4
  Category: writing
  Question: Known for her lush, poetic descriptions of the everyday, the book doesn’t contain traditional charac...
  -> Classifications: ['Misplaced Modifiers', 'Pronouns']

[258/416] Lesson: Phone Math #3, Q4
  Category: math
  Question: [[Diagram diagram-3]] What is the conjugate of this expression? (In other words, what’s the number y...
  -> No classifications matched

[259/416] Lesson: Colons, Q4
  Category: writing
  Question: It was rainy in Seattle: it was sunny in Los Angeles....
  -> Classifications: ['Colons', 'Combining Sentences']

[260/416] Lesson: Style Practice Questions, Q4
  Category: writing
  Question: If the writer were to break this paragraph into two, which would be the best place to start the new ...
  -> No classifications matched

[261/416] Lesson: Murder!, Q4
  Category: writing
  Question: Jordan— [4] *who’s* academic work was on [5] *fish, had* been president of Stanford since [6] *it’s*...
  -> Classifications: ['Who vs. Whom', 'Problematic Possessives']

[262/416] Lesson: Premium Grammar Practice #3, Q4
  Category: writing
  Question: Most of the students involved in the extensively planned and expertly coordinated *prank, are* still...
  -> Classifications: ['Commas', 'Verbs']

[263/416] Lesson: Practice #1, Q4
  Category: math
  Question: [[Diagram diagram-7]]
What is S in terms of N, A, H, and K?...
  -> Classifications: ['Fun with Functions', 'Equations']

[264/416] Lesson: Practice #2, Q4
  Category: math
  Question: The graph below plots the amount of time students in a homeroom class spend studying each night agai...
  -> Classifications: ['Stats', 'Word Problems']

[265/416] Lesson: Premium Practice #1, Q4
  Category: math
  Question: Below is a table of the vehicles in my apartment’s parking garage. [[Diagram diagram-6]] If I choose...
  -> Classifications: ['Probabilities']

[266/416] Lesson: Premium Grammar Practice #1, Q4
  Category: writing
  Question: The students who signed up *earliest, will* get the first choice of electives....
  -> Classifications: ['Combining Sentences', 'Misplaced Modifiers']

[267/416] Lesson: Factoring Practice, Q4
  Category: math
  Question: y = x² - 64 Which of the following options rewrites the function in a way that displays its solution...
  -> Classifications: ['Factoring Practice', 'Quadratic Functions']

[268/416] Lesson: Grammar Practice #2, Q4
  Category: writing
  Question: I wanted to play *basketball even though* it was raining....
  -> Classifications: ['Commas']

[269/416] Lesson: Probabilities, Q4
  Category: math
  Question: If you were to choose a third year student at random, what’s the likelihood that you’d choose one wh...
  -> Classifications: ['Probabilities']

[270/416] Lesson: Premium Practice #1, Q4
  Category: writing
  Question: *Consequently:* I’m not allowing back in the butterfly hut at the zoo anymore....
  -> Classifications: ['Transitional Expressions']

[271/416] Lesson: Five More Word Problems, Q4
  Category: math
  Question: My favorite TV show airs from 5 to 5:30 every Thursday. However, each episode is only 21 minutes lon...
  -> Classifications: ['Word Problems', 'Equations']

[272/416] Lesson: Function, Tone, and Phrasing, Q4
  Category: writing
  Question: Mrs. Simpson advocated the using of the extra funds to fix the potholes on Main Street....
  -> Classifications: ['Insertions, Deletions, and Revisions']

[273/416] Lesson: Premium Practice #2, Q4
  Category: math
  Question: Below is a graph relating my 400m dash times to the amount of time I allow myself between repetition...
  -> Classifications: ['Stats', 'Word Problems']

[274/416] Lesson: Commas, Q4
  Category: writing
  Question: *I kept driving straight even though I suspected that I was just going further and further away from...
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[275/416] Lesson: Practice #1, Q4
  Category: math
  Question: I only buy four colors of shirt: Carolina blue, light green, pink, and purple. I have each of them i...
  -> Classifications: ['Probabilities']

[276/416] Lesson: Surprising Singularity, Q4
  Category: writing
  Question: What should the verb be? Neither of them          enough respect....
  -> Classifications: ['Verbs']

[277/416] Lesson: Premium Practice #3, Q4
  Category: math
  Question: [[Diagram diagram-13]]

The expression above is equivalent to which of the following options?...
  -> No classifications matched

[278/416] Lesson: Math Diagnostic, Q4
  Category: math
  Question: My horrible cousin Throckmorton and I have had 46 water balloon fights. I’ve won eight more than Thr...
  -> Classifications: ['Systems of Equations', 'Word Problems']

[279/416] Lesson: Quick Practice #2, Q4
  Category: writing
  Question: The team *celebrate* the big win....
  -> Classifications: ['Verbs']

[280/416] Lesson: Premium Phone Math #3, Q4
  Category: math
  Question: What is the conjugate of this expression? (In other words, what’s the number you’d multiply both the...
  -> No classifications matched

[281/416] Lesson: Practice #4, Q4
  Category: math
  Question: y = x² + 3x - 10 If the vertex of the given parabola were written as (a, b), what would be the sum o...
  -> Classifications: ['Quadratic Functions']

[282/416] Lesson: Phone Math #1, Q4
  Category: math
  Question: Which of the following functions has three real solutions?...
  -> Classifications: ['Fun with Functions']

[283/416] Lesson: The Undead Merchant of Death, Q4
  Category: writing
  Question: Hence, when *it* thought he’d died, it ran an obituary calling him “the merchant of death.”...
  -> Classifications: ['Pronouns']

[284/416] Lesson: Circles, Q4
  Category: math
  Question: What are the center and radius of a circle which can be modeled with the equation (x - 5)² + (y + 5)...
  -> Classifications: ['Circles']

[285/416] Lesson: Premium Word Problems #3, Q4
  Category: math
  Question: Erliss is saving up money to go on a vacation. After four months, she has $120 in her vacation fund....
  -> Classifications: ['Word Problems']

[286/416] Lesson: Premium Practice #1, Q4
  Category: math
  Question: 2a^2 + 3(a - b) = 38
 a = 2 + b
 
Which of the following is a possible value for a?...
  -> Classifications: ['Equations', 'Word Problems']

[287/416] Lesson: Premium Practice #1, Q4
  Category: math
  Question: [[Diagram diagram-1]]

The total area of the circle is 80 inches². The area of the shaded region is ...
  -> Classifications: ['Circles', 'Missing Angles']

[288/416] Lesson: The Mexican Phoenix, Q4
  Category: writing
  Question: She had to be, girls were granted little access to education then....
  -> Classifications: ['Colons']

[289/416] Lesson: Phone Math #2, Q4
  Category: math
  Question: Which of the following is an example of exponential decay?...
  -> Classifications: ['Exponential Growth and Decay']

[290/416] Lesson: Practice #2, Q4
  Category: math
  Question: 2(x + y) + (y - x) = 20
 x = 7 - y
 What is the value of y - x?...
  -> Classifications: ['Systems of Equations', 'Linear Equations']

[291/416] Lesson: Premium Phone Math #1, Q4
  Category: math
  Question: Which of the following functions has four real solutions?...
  -> Classifications: ['Fun with Functions']

[292/416] Lesson: Premium Practice #2, Q4
  Category: writing
  Question: I was *early; he* was late....
  -> Classifications: ['Semicolons']

[293/416] Lesson: Premium Practice #1, Q4
  Category: writing
  Question: One of the 300 runners *wins* the race....
  -> Classifications: ['Verbs']

[294/416] Lesson: Practice #1, Q4
  Category: math
  Question: [[Diagram diagram-4]]

O is the center of the circle. A and B are points on the edge of the circle. ...
  -> Classifications: ['Circles', 'Word Problems']

[295/416] Lesson: Premium Practice #4, Q4
  Category: math
  Question: y = x² - 8x + 15  If the vertex of the given parabola were written as (c, d), what would be the prod...
  -> Classifications: ['Quadratic Functions']

[296/416] Lesson: Quadratic Functions, Q4
  Category: math
  Question: Below is the parabola created by the equation y = x² + 1.[[Diagram diagram-27]] Below is the parabol...
  -> Classifications: ['Quadratic Functions', 'Fun with Functions']

[297/416] Lesson: The Mexican Phoenix, Q5
  Category: writing
  Question: Juana herself was forbidden from entering her grandfather’s library; she had to break in and read in...
  -> Classifications: ['Semicolons']

[298/416] Lesson: Verb Practice, Q5
  Category: writing
  Question: Erliss is confident because she *done* all the reading for this unit....
  -> Classifications: ['Verbs']

[299/416] Lesson: Premium Practice #2, Q5
  Category: writing
  Question: *Who’s* s’mores backpack is this?...
  -> Classifications: ['Problematic Possessives']

[300/416] Lesson: Style Practice Questions, Q5
  Category: writing
  Question: Which of the choices provides the best transition from the previous paragraph to the one that follow...
  -> Classifications: ['Introductions, Transitions, and Conclusions']

[301/416] Lesson: Premium Grammar Practice #2, Q5
  Category: writing
  Question: I finished my homework as soon as I got home, *that allowed* me to marathon 12 straight episodes of ...
  -> Classifications: ['Combining Sentences', 'Verbs']

[302/416] Lesson: Five More Word Problems, Q5
  Category: math
  Question: I have to read two books for school tomorrow: a novel and a textbook. I can read 45 pages of the nov...
  -> Classifications: ['Word Problems']

[303/416] Lesson: Quick Practice #2, Q5
  Category: writing
  Question: If you leave now, *than* you’ll never know the answer....
  -> Classifications: ['Function, Tone, and Phrasing']

[304/416] Lesson: Quick Practice #2, Q5
  Category: writing
  Question: *Its’ time.*...
  -> Classifications: ['Apostrophes']

[305/416] Lesson: Quick Practice #1, Q5
  Category: writing
  Question: The *childrens’* faces gaped at me: I’d turned red....
  -> Classifications: ['Problematic Possessives', 'Apostrophes']

[306/416] Lesson: Commas, Q5
  Category: writing
  Question: Which version works?...
  -> Classifications: ['Combining Sentences']

[307/416] Lesson: Premium Grammar Practice #1, Q5
  Category: writing
  Question: Being on the quiz bowl team didn’t have as many perks as, say, being a starter on the football team....
  -> Classifications: ['Function, Tone, and Phrasing', 'Transitional Expressions']

[308/416] Lesson: Probabilities, Q5
  Category: math
  Question: If a student from these grades is chosen at random, what’s the likelihood that the student will be a...
  -> No classifications matched

[309/416] Lesson: Premium Grammar Practice #3, Q5
  Category: writing
  Question: The word “solutions” *is* synonymous with “zeros,” the values for x that make the whole function equ...
  -> Classifications: ['Verbs']

[310/416] Lesson: The Waves, Q5
  Category: writing
  Question: *Therefore*, the story is told by six voices— three female and three male— which presents less of a ...
  -> Classifications: ['Transitional Expressions']

[311/416] Lesson: Grammar Practice #2, Q5
  Category: writing
  Question: I made ate a midnight snack of leftovers from the *fridge, including:* turkey, ham, stuffing, mashed...
  -> Classifications: ['Colons']

[312/416] Lesson: Function, Tone, and Phrasing, Q5
  Category: writing
  Question: Erliss sets aside money each week as a means for saving up enough cash to go on vacation....
  -> Classifications: ['Function, Tone, and Phrasing']

[313/416] Lesson: Premium Practice #2, Q5
  Category: math
  Question: Below is a graph relating my 400m dash times to the amount of time I allow myself between repetition...
  -> Classifications: ['Stats']

[314/416] Lesson: Grammar Practice #1, Q5
  Category: writing
  Question: Vassar was founded as a *womens’ college*....
  -> Classifications: ['Problematic Possessives', 'Apostrophes']

[315/416] Lesson: Murder!, Q5
  Category: writing
  Question: Jordan— [4] *who’s* academic work was on [5] *fish, had* been president of Stanford since [6] *it’s*...
  -> Classifications: ['Dashes and Parentheses', 'Problematic Possessives']

[316/416] Lesson: Premium Practice #1, Q5
  Category: writing
  Question: *She laughed, he smiled.*...
  -> Classifications: ['Semicolons']

[317/416] Lesson: Factoring Practice, Q5
  Category: math
  Question: y = 3x² + 6x - 45
 What is one factor of the equation?...
  -> Classifications: ['Factoring Practice', 'Quadratic Functions']

[318/416] Lesson: Equations, Q5
  Category: math
  Question: [[Diagram diagram-4]] If x = 1 and a > 0, what does a equal?...
  -> No classifications matched

[319/416] Lesson: My Belovèd Hoodie, Q5
  Category: writing
  Question: More importantly, it was almost superfluously [6] soft, it fit absolutely perfectly....
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[320/416] Lesson: Five Word Problems, Q5
  Category: math
  Question: There are two different ride-sharing companies in my city. CRZ charges a $1.00 flat rate plus $0.50 ...
  -> Classifications: ['Inequalities', 'Word Problems']

[321/416] Lesson: Grammar Practice #3, Q5
  Category: writing
  Question: The class, which is made up of 15 juniors and 12 seniors, *meet* in room 237....
  -> Classifications: ['Verbs']

[322/416] Lesson: Quick Practice #1, Q5
  Category: writing
  Question: Everyone *are* going crazy....
  -> Classifications: ['Verbs']

[323/416] Lesson: Practice #2, Q5
  Category: math
  Question: The graph below plots the amount of time students in a homeroom class spend studying each night agai...
  -> Classifications: ['Stats', 'Word Problems']

[324/416] Lesson: Premium Practice #1, Q5
  Category: writing
  Question: Each one of you *knows* which way is best for yourself....
  -> Classifications: ['Verbs']

[325/416] Lesson: Premium Practice #2, Q5
  Category: writing
  Question: Before I met the angelic Erliss, I *had not thought* that a person could be so wonderful....
  -> Classifications: ['Verbs']

[326/416] Lesson: The Undead Merchant of Death, Q5
  Category: writing
  Question: Nobel was shocked to see his impact on the world put in such stark terms. *Nobel was shocked to see ...
  -> Classifications: ['Combining Sentences']

[327/416] Lesson: Math Diagnostic, Q5
  Category: math
  Question: For his spring semester, Upfish achieved a GPA of 3.85. This is a 10% increase from his GPA during h...
  -> Classifications: ['Word Problems']

[328/416] Lesson: The Mexican Phoenix, Q6
  Category: writing
  Question: When she was a teenager, de la Cruz devises a plan to dress as a boy and attend college (which was r...
  -> Classifications: ['Verbs']

[329/416] Lesson: Murder!, Q6
  Category: writing
  Question: Jordan— [4] *who’s* academic work was on [5] *fish, had* been president of Stanford since [6] *it’s*...
  -> Classifications: ['Problematic Possessives']

[330/416] Lesson: Premium Grammar Practice #2, Q6
  Category: writing
  Question: The quiz bowl team, including four starters and two alternates, hoisted *their* trophy into the air....
  -> Classifications: ['Pronouns', 'Problematic Possessives']

[331/416] Lesson: Commas, Q6
  Category: writing
  Question: Which version works?...
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[332/416] Lesson: The Waves, Q6
  Category: writing
  Question: The story is told by six voices— three female and three male— which *presents* less of a scene-by-sc...
  -> Classifications: ['Verbs']

[333/416] Lesson: Premium Grammar Practice #3, Q6
  Category: writing
  Question: I don’t know *whom* to believe....
  -> Classifications: ['Who vs. Whom']

[334/416] Lesson: Grammar Practice #1, Q6
  Category: writing
  Question: Even though I got back from the beach weeks ago, I’m still finding sand everywhere: in my shoes, bet...
  -> Classifications: ['Parallel Structure', 'Insertions, Deletions, and Revisions']

[335/416] Lesson: Grammar Practice #3, Q6
  Category: writing
  Question: Someone *needs* to tell me who stole my Batman cup right now!...
  -> Classifications: ['Verbs']

[336/416] Lesson: My Belovèd Hoodie, Q6
  Category: writing
  Question: The writer is thinking of deleting the preceding sentence. Should the writer make this deletion?...
  -> Classifications: ['Insertions, Deletions, and Revisions']

[337/416] Lesson: The Undead Merchant of Death, Q6
  Category: writing
  Question: In 1888, Alfred Nobel’s brother died. *However*, some newspapers misreported it as Alfred’s death....
  -> Classifications: ['Transitional Expressions']

[338/416] Lesson: Premium Grammar Practice #1, Q6
  Category: writing
  Question: All of the passengers *is relieved* when the turbulence stopped....
  -> Classifications: ['Verbs']

[339/416] Lesson: Equations, Q6
  Category: math
  Question: [[Diagram diagram-10]] What does x equal?...
  -> No classifications matched

[340/416] Lesson: Verb Practice, Q6
  Category: writing
  Question: Yesterday, I came. Today, I *see*. Tomorrow, I conquer....
  -> Classifications: ['Verbs']

[341/416] Lesson: Math Diagnostic, Q6
  Category: math
  Question: Erliss is celebrating her last day at her old job by visiting her favorite diner. Cheeseburgers cost...
  -> Classifications: ['Word Problems', 'Proportions']

[342/416] Lesson: Grammar Practice #2, Q6
  Category: writing
  Question: After winning the championship, our coach was overcome *in* emotion....
  -> Classifications: ['Function, Tone, and Phrasing']

[343/416] Lesson: Style Practice Questions, Q6
  Category: writing
  Question: Which option is most consistent with the tone established in the passage?...
  -> No classifications matched

[344/416] Lesson: Math Diagnostic, Q7
  Category: math
  Question: [[Diagram diagram-2]] (The figure is not drawn to scale.) GB is perpendicular to DF and AC and it di...
  -> Classifications: ['Triangles', 'Word Problems']

[345/416] Lesson: Murder!, Q7
  Category: writing
  Question: He butted heads with Mrs. Stanford over most [7] *things;* the budget, the focus of the curriculum, ...
  -> Classifications: ['Colons']

[346/416] Lesson: Premium Grammar Practice #1, Q7
  Category: writing
  Question: *You* can add or subtract fractions only after we make the denominators equal....
  -> Classifications: ['Pronouns']

[347/416] Lesson: Grammar Practice #2, Q7
  Category: writing
  Question: I had a busy day planned. *However*, at 4pm I had to be at basketball practice while simultaneously ...
  -> Classifications: ['Transitional Expressions']

[348/416] Lesson: Grammar Practice #1, Q7
  Category: writing
  Question: Don’t try to tell *Throckmorton and me* to end our age-old feud....
  -> Classifications: ['Pronouns']

[349/416] Lesson: Premium Grammar Practice #3, Q7
  Category: writing
  Question: *Actor and comedian, Aziz Ansari* is known for his love of food....
  -> Classifications: ['Commas']

[350/416] Lesson: Verb Practice, Q7
  Category: writing
  Question: He *wakes* up at 5 am to go to practice every day because he wanted to earn a swimming scholarship....
  -> Classifications: ['Verbs']

[351/416] Lesson: The Waves, Q7
  Category: writing
  Question: The voices are *commenced* by nine short, poetic interludes: the ebb and flow of a tide from sunrise...
  -> Classifications: ['Function, Tone, and Phrasing']

[352/416] Lesson: Equations, Q7
  Category: math
  Question: 2(x² + 3x - 1) + 3x(x + 2) = ?...
  -> Classifications: ['Factoring Practice', 'Linear Equations']

[353/416] Lesson: Premium Grammar Practice #2, Q7
  Category: writing
  Question: Everyone on the plane *smells* the pancakes that the gentleman in 3C has started eating....
  -> Classifications: ['Verbs']

[354/416] Lesson: The Mexican Phoenix, Q7
  Category: writing
  Question: When she was a teenager, de la Cruz devises a plan to dress as a boy and attend college (which was r...
  -> Classifications: ['Combining Sentences', 'Transitional Expressions']

[355/416] Lesson: Grammar Practice #3, Q7
  Category: writing
  Question: They tried to pretend that they were 12 so they’d only have to pay for *childrens* tickets....
  -> Classifications: ['Problematic Possessives', 'Apostrophes']

[356/416] Lesson: The Undead Merchant of Death, Q7
  Category: writing
  Question: Much akin with Tom Sawyer listening in on his own funeral service, Nobel got the chance to see what ...
  -> Classifications: ['Function, Tone, and Phrasing']

[357/416] Lesson: Style Practice Questions, Q7
  Category: writing
  Question: What's the most logical and effective placement for sentence F?...
  -> No classifications matched

[358/416] Lesson: My Belovèd Hoodie, Q7
  Category: writing
  Question: This makes it all the more tragic that I am personally guilt of accidentally destroying my belovèd h...
  -> Classifications: ['Introductions, Transitions, and Conclusions']

[359/416] Lesson: Grammar Practice #2, Q8
  Category: writing
  Question: Running and jumping through the halls, *celebrating* the end of the school year....
  -> Classifications: ['Insertions, Deletions, and Revisions', 'Misplaced Modifiers']

[360/416] Lesson: Premium Grammar Practice #2, Q8
  Category: writing
  Question: The lizard, the rabbit, and the dog sprinted out of their cages. *It* leapt out of the open screen d...
  -> Classifications: ['Pronouns']

[361/416] Lesson: Math Diagnostic, Q8
  Category: math
  Question: y = 8x² - 4x + 2  How many real solutions are there to this equation?...
  -> Classifications: ['Quadratic Formula', 'Quadratic Functions']

[362/416] Lesson: Murder!, Q8
  Category: writing
  Question: She wanted to invite philosophers [8] *(such as the famous William James)* to campus....
  -> Classifications: ['Dashes and Parentheses']

[363/416] Lesson: My Belovèd Hoodie, Q8
  Category: writing
  Question: I’d been wearing it even more than usual: in class, at meals, and [9] I wore the hoodie during my ni...
  -> Classifications: ['Parallel Structure']

[364/416] Lesson: The Mexican Phoenix, Q8
  Category: writing
  Question: To make this paragraph most logical, sentence D should be placed......
  -> Classifications: ['Moving Sentences', 'Introductions, Transitions, and Conclusions']

[365/416] Lesson: The Waves, Q8
  Category: writing
  Question: Woolf was aiming for a musical effect....
  -> No classifications matched

[366/416] Lesson: Style Practice Questions, Q8
  Category: writing
  Question: Which of the following options provides the best conclusion for the passage?...
  -> No classifications matched

[367/416] Lesson: Grammar Practice #1, Q8
  Category: writing
  Question: The implausibility of events that transpire in the scene *are* so astounding that I laugh out loud....
  -> Classifications: ['Verbs']

[368/416] Lesson: The Undead Merchant of Death, Q8
  Category: writing
  Question: Nobel was *displaced* to devote his time and resources to philanthropy....
  -> Classifications: ['Function, Tone, and Phrasing']

[369/416] Lesson: Premium Grammar Practice #1, Q8
  Category: writing
  Question: It’s like Christmas when a big box of jobs *arrive* from our printer....
  -> Classifications: ['Verbs']

[370/416] Lesson: Verb Practice, Q8
  Category: writing
  Question: Nine out of ten dentists *says* the same thing....
  -> Classifications: ['Verbs']

[371/416] Lesson: Premium Grammar Practice #3, Q8
  Category: writing
  Question: *Knowing* that we’d cause countless interruptions if we were near each other, our French teacher sit...
  -> Classifications: ['Verbs']

[372/416] Lesson: Grammar Practice #3, Q8
  Category: writing
  Question: *Its* our chance to go nuts!...
  -> Classifications: ['Problematic Possessives', 'Pronouns']

[373/416] Lesson: The Undead Merchant of Death, Q9
  Category: writing
  Question: His most famous attempt to inspire positive change was his endowment of the Nobel Prize, for which h...
  -> No classifications matched

[374/416] Lesson: The Waves, Q9
  Category: writing
  Question: At *it’s* best, the novel does indeed achieve a sort of lyricism, set against the percussive backbea...
  -> Classifications: ['Problematic Possessives']

[375/416] Lesson: Grammar Practice #2, Q9
  Category: writing
  Question: We can eliminate incorrect answers in the Reading section if they provide information that contradic...
  -> No classifications matched

[376/416] Lesson: Murder!, Q9
  Category: writing
  Question: She also had a bit of an occult streak, and she was very interested [9] *into* research into spiritu...
  -> Classifications: ['Function, Tone, and Phrasing']

[377/416] Lesson: Verb Practice, Q9
  Category: writing
  Question: One of my favorite players *are* Giannis....
  -> Classifications: ['Verbs']

[378/416] Lesson: My Belovèd Hoodie, Q9
  Category: writing
  Question: I wore my blue hoodie almost as much as any other hoodie I owned. [10]...
  -> Classifications: ['Combining Sentences', 'Function, Tone, and Phrasing']

[379/416] Lesson: Grammar Practice #1, Q9
  Category: writing
  Question: I sat down at my *desk; I discovered* that someone had placed a large thumbtack rightside up on my s...
  -> Classifications: ['Semicolons']

[380/416] Lesson: Grammar Practice #3, Q9
  Category: writing
  Question: Erliss plans *on* spending exactly $20....
  -> Classifications: ['Function, Tone, and Phrasing']

[381/416] Lesson: Premium Grammar Practice #3, Q9
  Category: writing
  Question: Our *teachers who* know of our long-running feud— make sure to keep my cousin Throckmorton and me se...
  -> Classifications: ['Dashes and Parentheses']

[382/416] Lesson: Premium Grammar Practice #1, Q9
  Category: writing
  Question: While rain lashed against the windows, *drinking* the hot chocolate they’d just brewed up....
  -> Classifications: ['Verbs']

[383/416] Lesson: Math Diagnostic, Q9
  Category: math
  Question: RF = PQ - R What is R in terms of F, P, and Q?...
  -> Classifications: ['Equations', 'Linear Equations']

[384/416] Lesson: Premium Grammar Practice #2, Q9
  Category: writing
  Question: Our ragtag team of beginners, outcasts, and *goofballs, somehow* made it to the championship....
  -> Classifications: ['Commas']

[385/416] Lesson: The Mexican Phoenix, Q9
  Category: writing
  Question: Sor Juana (who’s literary career started when she wrote a poem about the Eucharist at the age of eig...
  -> Classifications: ['Problematic Possessives']

[386/416] Lesson: Grammar Practice #3, Q10
  Category: writing
  Question: *Floppy-eared and droopy-eyed, I fell in love with the dog.*...
  -> Classifications: ['Misplaced Modifiers']

[387/416] Lesson: The Waves, Q10
  Category: writing
  Question: There are *some, truly ecstatic scenes and entrancing interludes, in the book.*...
  -> Classifications: ['Commas']

[388/416] Lesson: Premium Grammar Practice #3, Q10
  Category: writing
  Question: *Upfish’s* test results came back— he got a 97%!...
  -> Classifications: ['Problematic Possessives', 'Apostrophes']

[389/416] Lesson: Premium Grammar Practice #2, Q10
  Category: writing
  Question: His lucky penny— not his expensive clothes or his two 70” televisions— *is* the only thing the burgl...
  -> Classifications: ['Dashes and Parentheses', 'Surprising Singularity']

[390/416] Lesson: Grammar Practice #1, Q10
  Category: writing
  Question: The thing about ninjas is that *they’re always absolutely on top of their* game....
  -> Classifications: ['Pronouns', 'Problematic Possessives']

[391/416] Lesson: Premium Grammar Practice #1, Q10
  Category: writing
  Question: Rosalind put on men’s clothing, *changes her name to* Ganymede, and hid out in the forest....
  -> Classifications: ['Parallel Structure']

[392/416] Lesson: The Mexican Phoenix, Q10
  Category: writing
  Question: Sor Juana (whose literary career started when she wrote a poem about the Eucharist at the age of eig...
  -> Classifications: ['Dashes and Parentheses']

[393/416] Lesson: Grammar Practice #2, Q10
  Category: writing
  Question: *Every year, my GPA jumped by a quarter of a point during the Spring Term.* Which option most accura...
  -> No classifications matched

[394/416] Lesson: The Undead Merchant of Death, Q10
  Category: writing
  Question: To this day, the Nobel Prize is awarded *to recipients who have distinguished themselves* in physica...
  -> Classifications: ['Insertions, Deletions, and Revisions']

[395/416] Lesson: Verb Practice, Q10
  Category: writing
  Question: Erliss *will know* that she was ready for the vocab quiz when she could recite all of her words from...
  -> Classifications: ['Verbs']

[396/416] Lesson: My Belovèd Hoodie, Q10
  Category: writing
  Question: In May however it got so hot that I couldn’t wear the hoodie comfortably anymore. [11]...
  -> Classifications: ['Transitional Expressions', 'Commas']

[397/416] Lesson: Math Diagnostic, Q10
  Category: math
  Question: (x - 5)² + (y - 5)² = 16.  Does the circle created by this equation contain the origin?...
  -> Classifications: ['Circles']

[398/416] Lesson: Murder!, Q10
  Category: writing
  Question: Jordan, [10] *therefore*, argued that the school should focus on the hard sciences....
  -> Classifications: ['Transitional Expressions']

[399/416] Lesson: Grammar Practice #3, Q11
  Category: writing
  Question: Painter Salvador Dali was fascinated *of* rhinoceroses....
  -> Classifications: ['Function, Tone, and Phrasing']

[400/416] Lesson: The Undead Merchant of Death, Q11
  Category: writing
  Question: As of 2018, 584 prizes have been given out....
  -> Classifications: ['Introductions, Transitions, and Conclusions']

[401/416] Lesson: My Belovèd Hoodie, Q11
  Category: writing
  Question: I threw it in the back of my car and forgot about it until September, when it was finally chilly eno...
  -> Classifications: ['Verbs']

[402/416] Lesson: The Waves, Q11
  Category: writing
  Question: The writer is thinking of deleting the previous sentence. Should the writer do so?...
  -> No classifications matched

[403/416] Lesson: Grammar Practice #1, Q11
  Category: writing
  Question: I have to jog five miles a day just to *prolong* my current level of physical fitness....
  -> Classifications: ['Function, Tone, and Phrasing']

[404/416] Lesson: The Mexican Phoenix, Q11
  Category: writing
  Question: Sor Juana wrote plays, poems, and completed the composition of philosophical tracts....
  -> Classifications: ['Parallel Structure']

[405/416] Lesson: Grammar Practice #2, Q11
  Category: writing
  Question: The month after the tornado struck was a very *trying* time for my family....
  -> Classifications: ['Function, Tone, and Phrasing']

[406/416] Lesson: Murder!, Q11
  Category: writing
  Question: What’s the best placement of sentence [B]?...
  -> Classifications: ['Moving Sentences', 'Introductions, Transitions, and Conclusions']

[407/416] Lesson: Premium Grammar Practice #3, Q11
  Category: writing
  Question: *They’re* launching a full-scale investigation....
  -> Classifications: ['Pronouns']

[408/416] Lesson: Premium Grammar Practice #1, Q11
  Category: writing
  Question: I was able to turn in my thesis on *time (even though I had to type the final 15 pages the night bef...
  -> Classifications: ['Dashes and Parentheses', 'Combining Sentences']

[409/416] Lesson: The Undead Merchant of Death, Q12
  Category: writing
  Question: What is the most logical and effective placement for paragraph 3?...
  -> Classifications: ['Moving Sentences', 'Introductions, Transitions, and Conclusions']

[410/416] Lesson: The Mexican Phoenix, Q12
  Category: writing
  Question: She had to stop writing and was forced to sell her extensive library containing no less then 4,000 v...
  -> Classifications: ['Problematic Possessives']

[411/416] Lesson: My Belovèd Hoodie, Q12
  Category: writing
  Question: Balled up for an entire summer, it had lost [13] it’s shape....
  -> Classifications: ['Problematic Possessives']

[412/416] Lesson: Murder!, Q12
  Category: writing
  Question: [12] *They’re* conflict went on for years....
  -> Classifications: ['Problematic Possessives']

[413/416] Lesson: Murder!, Q13
  Category: writing
  Question: At the time of her death, Jane Stanford was planning [13] *for* firing Jordan....
  -> Classifications: ['Function, Tone, and Phrasing']

[414/416] Lesson: The Mexican Phoenix, Q13
  Category: writing
  Question: Recently, however, Sor Juana has received renewed interest....
  -> Classifications: ['Introductions, Transitions, and Conclusions']

[415/416] Lesson: My Belovèd Hoodie, Q13
  Category: writing
  Question: I’ve worn many hooded sweatshirts since [14] then, but sadly, none of them have ever felt the same....
  -> Classifications: ['Combining Sentences', 'Commas']

[416/416] Lesson: The Mexican Phoenix, Q14
  Category: writing
  Question: Everyone who has the pleasure of coming across an anthology of her work is bound to be blown away by...
  -> Classifications: ['Pronouns']

Lesson Questions: Classified 377, Skipped 0

=== Processing Passage Questions ===
Found 143 passage questions to process

[1/143] [From passage: Joyce, Hemingway, and Barfights]
Q1: The author of this passage:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[2/143] [From passage: The Creation and Destruction of the Globe]
Q1: The primary purpose of the passage is to:...
  -> Classifications: ['Overarching purpose']

[3/143] [From passage: Which Glove Do You Like Best?]
Q1: What is the main point of this passage?...
  -> Classifications: ['Overarching purpose']

[4/143] [From passage: Poet, Playwright, and... Spy?]
Q1: The author views the theory that Marlowe was a spy as:...
  -> Classifications: ['Use of evidence']

[5/143] [From passage: Collegiate Athletics]
Q1: What does the author of Passage 1 argue about the historical roots of the NCAA?...
  -> Classifications: ['Use of evidence']

[6/143] [From passage: Apocalyptic Advertising]
Q1: The main argument of this passage is that:...
  -> Classifications: ['Overarching purpose']

[7/143] [From passage: Invisible Rivers, Invisible Bridges]
Q1: The author of this passage views Nixon as:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[8/143] [From passage: Fund the Metro!]
Q1: The passage is written from the perspective of:...
  -> No classifications matched

[9/143] [From passage: Down with Data Centers]
Q1: The author thinks that new data centers:...
  -> Classifications: ['Overarching purpose']

[10/143] [From passage: Postcards from 100 Boots]
Q1: The main purpose of the passage is to:...
  -> Classifications: ['Overarching purpose']

[11/143] [From passage: The Comedies]
Q1: Why does the author think that people should read Shakespeare’s comedies multipl...
  -> Classifications: ['Use of evidence']

[12/143] [From passage: Phrenology]
Q1: The author’s view of phrenology can be best described as:...
  -> No classifications matched

[13/143] [From passage: Civic Engagement]
Q1: What is the meaning of the word “lackeys” in line 6?...
  -> Classifications: ['Word-in-context']

[14/143] [From passage: Am I a novelist?]
Q1: What is the main point of the passage?...
  -> Classifications: ['Overarching purpose']

[15/143] [From passage: Who's watching over me?]
Q1: According to the passage:...
  -> Classifications: ['Use of evidence']

[16/143] [From passage: The Stanford Prison Experiment]
Q1: The main purpose of the passage is to:...
  -> Classifications: ['Overarching purpose']

[17/143] [From passage: The Blue Eyes/Brown Eyes Experiment]
Q1: Overall, the author's view of Ms. Elliot's work is:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[18/143] [From passage: In the Mood for Love]
Q1: The word “painterly,” as it’s used in line 6, most nearly means:...
  -> Classifications: ['Word-in-context']

[19/143] [From passage: “Pistol” Pete Maravich]
Q1: According to the passage, how many years did Pete Maravich’s basketball training...
  -> No classifications matched

[20/143] [From passage: Let Sleeping Children Lie]
Q1: The main purpose of the passage is to:...
  -> Classifications: ['Overarching purpose']

[21/143] [From passage: Connie “The Hawk” Hawkins]
Q1: The author's attitude towards Hawkins is best described as:...
  -> Classifications: ['Use of evidence']

[22/143] [From passage: The Longshoreman Philosopher]
Q1: What is the overall structure of the passage?...
  -> No classifications matched

[23/143] [From passage: How smart are you?]
Q1: How would the author of this passage likely feel about intelligence tests?...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[24/143] [From passage: Civic Engagement]
Q2: The author of Passage 1 would likely respond to the argument presented in lines ...
  -> Classifications: ['Use of evidence']

[25/143] [From passage: How smart are you?]
Q2: The author mentions height and weight in order to:...
  -> Classifications: ['Overarching purpose']

[26/143] [From passage: Apocalyptic Advertising]
Q2: In the context of the passage, “‘It’ll change everything— it might destroy the w...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[27/143] [From passage: Who's watching over me?]
Q2: What is the 'illusion' mentioned in line 17?...
  -> Classifications: ['Line reading', 'Use of evidence']

[28/143] [From passage: The Stanford Prison Experiment]
Q2: Overall, the author’s view of the Stanford Prison Experiment can be best describ...
  -> Classifications: ['Overarching purpose']

[29/143] [From passage: Poet, Playwright, and... Spy?]
Q2: The author states that there's a lack of documentation about Marlowe's life beca...
  -> Classifications: ['Use of evidence']

[30/143] [From passage: Which Glove Do You Like Best?]
Q2: The author sees the human brain as:...
  -> Classifications: ['Overarching purpose']

[31/143] [From passage: Phrenology]
Q2: The main purpose of the first paragraph (lines 1-14) is to:...
  -> Classifications: ['Overarching purpose']

[32/143] [From passage: Fund the Metro!]
Q2: As it's used in line 2, the phrase “frankly unacceptable” means:...
  -> Classifications: ['Word-in-context']

[33/143] [From passage: Postcards from 100 Boots]
Q2: Lines 2-6 (“Andy… images.”) serve to:...
  -> Classifications: ['Use of evidence']

[34/143] [From passage: “Pistol” Pete Maravich]
Q2: In the context of the first paragraph, “especially because Maravich grew up in t...
  -> Classifications: ['Use of evidence']

[35/143] [From passage: The Creation and Destruction of the Globe]
Q2: As used in line 7, the word “vice” most nearly means:...
  -> Classifications: ['Word-in-context']

[36/143] [From passage: The Comedies]
Q2: In the context of the passage, the word “music“ in line 8 is:...
  -> Classifications: ['Word-in-context']

[37/143] [From passage: Joyce, Hemingway, and Barfights]
Q2: In the context of the passage, the parenthetical remarks “(Joyce the cunning… pu...
  -> Classifications: ['Use of evidence']

[38/143] [From passage: The Longshoreman Philosopher]
Q2: According to the author of the passage, most intellectuals’ lives are:...
  -> Classifications: ['Line reading', 'Use of evidence']

[39/143] [From passage: The Blue Eyes/Brown Eyes Experiment]
Q2: During the experiment, students in the privileged group:...
  -> Classifications: ['Line reading', 'Use of evidence']

[40/143] [From passage: Am I a novelist?]
Q2: Proust asking himself “Am I a novelist?” is ironic to readers now because:...
  -> No classifications matched

[41/143] [From passage: Connie “The Hawk” Hawkins]
Q2: As it's used in line 2, the word “galling” most nearly means:...
  -> Classifications: ['Word-in-context']

[42/143] [From passage: Let Sleeping Children Lie]
Q2: The author bases his or her argument on:...
  -> Classifications: ['Use of evidence']

[43/143] [From passage: Collegiate Athletics]
Q2: As it's used in line 16, “moralistic” most nearly means:...
  -> Classifications: ['Word-in-context']

[44/143] [From passage: Invisible Rivers, Invisible Bridges]
Q2: Which words provide the best evidence for the answer to question 1?...
  -> Classifications: ['Use of evidence']

[45/143] [From passage: In the Mood for Love]
Q2: The author mentions silent film in order to:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[46/143] [From passage: Down with Data Centers]
Q2: The best evidence for the answer to question 1 is:...
  -> Classifications: ['Use of evidence']

[47/143] [From passage: Collegiate Athletics]
Q3: The author of Passage 1 put quotation marks around “education” in line 20 in ord...
  -> Classifications: ['Line reading', 'Word-in-context']

[48/143] [From passage: Am I a novelist?]
Q3: Which of the following choices provides the best evidence for the previous quest...
  -> Classifications: ['Use of evidence']

[49/143] [From passage: The Creation and Destruction of the Globe]
Q3: The time that it took to build The Globe in 1599:...
  -> Classifications: ['Use of evidence']

[50/143] [From passage: Fund the Metro!]
Q3: The first paragraph (lines 1-17) serves to:...
  -> Classifications: ['Overarching purpose']

[51/143] [From passage: Apocalyptic Advertising]
Q3: The author’s stance towards the AI companies’ promises about oversight can be be...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[52/143] [From passage: Down with Data Centers]
Q3: As it’s used in line X, the word “frankly” most nearly means:...
  -> Classifications: ['Word-in-context']

[53/143] [From passage: Let Sleeping Children Lie]
Q3: As used in line 14, the word 'conservative' most nearly means:...
  -> Classifications: ['Word-in-context']

[54/143] [From passage: Which Glove Do You Like Best?]
Q3: Which choice provides the best evidence for the answer to the previous question?...
  -> Classifications: ['Use of evidence']

[55/143] [From passage: “Pistol” Pete Maravich]
Q3: Maravich was called “Pistol” Pete because:...
  -> Classifications: ['Line reading', 'Use of evidence']

[56/143] [From passage: The Stanford Prison Experiment]
Q3: As it’s used in line 3, “dubious” most nearly means:...
  -> Classifications: ['Word-in-context']

[57/143] [From passage: Connie “The Hawk” Hawkins]
Q3: Hawkins's playing style can be best described as:...
  -> No classifications matched

[58/143] [From passage: How smart are you?]
Q3: In the context of the passage, the questions in lines 22-28 (“Is your IQ… tuck i...
  -> Classifications: ['Use of evidence']

[59/143] [From passage: Invisible Rivers, Invisible Bridges]
Q3: In the parenthetical remark in line 12(“including, simply to feel important and ...
  -> Classifications: ['Line reading', 'Use of evidence']

[60/143] [From passage: Phrenology]
Q3: As used in line 1, “romantic” most nearly means:...
  -> Classifications: ['Word-in-context']

[61/143] [From passage: Postcards from 100 Boots]
Q3: In the passage, Mark Rothko was associated with which artistic movement?...
  -> Classifications: ['Use of evidence']

[62/143] [From passage: Poet, Playwright, and... Spy?]
Q3: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[63/143] [From passage: The Blue Eyes/Brown Eyes Experiment]
Q3: As it's used in line 23, the word “resigned” most nearly means:...
  -> Classifications: ['Word-in-context']

[64/143] [From passage: The Longshoreman Philosopher]
Q3: As used in line 25, the word “odd” most nearly means:...
  -> Classifications: ['Word-in-context']

[65/143] [From passage: Civic Engagement]
Q3: Which choice provides the best evidence for the above question?...
  -> Classifications: ['Use of evidence']

[66/143] [From passage: Civic Engagement]
Q4: The author of Passage 1 mentions voters who support third-party candidates in or...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[67/143] [From passage: Postcards from 100 Boots]
Q4: Antin's work can be described as:...
  -> Classifications: ['Use of evidence']

[68/143] [From passage: Connie “The Hawk” Hawkins]
Q4: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[69/143] [From passage: Am I a novelist?]
Q4: As it's used in line 32, the word “acute” most nearly means:...
  -> Classifications: ['Word-in-context']

[70/143] [From passage: Poet, Playwright, and... Spy?]
Q4: Marlowe received his MA degree:...
  -> Classifications: ['Use of evidence']

[71/143] [From passage: Let Sleeping Children Lie]
Q4: One concession to practicality that the author makes is to admit that:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[72/143] [From passage: Collegiate Athletics]
Q4: As it's used in line 22, “skirt” most nearly means:...
  -> Classifications: ['Word-in-context']

[73/143] [From passage: Which Glove Do You Like Best?]
Q4: As used in line 16, “fudged” most nearly means:...
  -> Classifications: ['Word-in-context']

[74/143] [From passage: The Stanford Prison Experiment]
Q4: How many of the participants were assigned to be prisoners?...
  -> Classifications: ['Use of evidence']

[75/143] [From passage: The Longshoreman Philosopher]
Q4: One thing that set The True Believer apart from other works of history and socio...
  -> Classifications: ['Use of evidence']

[76/143] [From passage: The Blue Eyes/Brown Eyes Experiment]
Q4: The author mentions the superior academic performance of the blue-eyed children ...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[77/143] [From passage: Phrenology]
Q4: According to the passage, phrenology:...
  -> No classifications matched

[78/143] [From passage: Fund the Metro!]
Q4: The author views LA's roads as:...
  -> Classifications: ['Overarching purpose']

[79/143] [From passage: “Pistol” Pete Maravich]
Q4: In the context of the passage, “It wasn’t just shooting, though” (line 18) serve...
  -> Classifications: ['Line reading', 'Use of evidence']

[80/143] [From passage: The Creation and Destruction of the Globe]
Q4: In the third paragraph (lines 25-35), the author states that the new theater's n...
  -> Classifications: ['Line reading', 'Use of evidence']

[81/143] [From passage: The Creation and Destruction of the Globe]
Q5: According to the passage, the destruction of The Globe:...
  -> Classifications: ['Use of evidence']

[82/143] [From passage: The Stanford Prison Experiment]
Q5: As it’s used in line 24, “approximate” most nearly means:...
  -> Classifications: ['Word-in-context']

[83/143] [From passage: “Pistol” Pete Maravich]
Q5: In the context of the fifth paragraph, the word “preternatural” (line 29) most n...
  -> Classifications: ['Word-in-context']

[84/143] [From passage: The Longshoreman Philosopher]
Q5: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[85/143] [From passage: Collegiate Athletics]
Q5: The reference to the “liberating wisdom of the ancient humanistic tradition” in ...
  -> Classifications: ['Use of evidence']

[86/143] [From passage: Let Sleeping Children Lie]
Q5: Which of the choices provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[87/143] [From passage: The Blue Eyes/Brown Eyes Experiment]
Q5: The participants in the experiment:...
  -> No classifications matched

[88/143] [From passage: Am I a novelist?]
Q5: Proust's life before 1908 was one of:...
  -> Classifications: ['Line reading', 'Use of evidence']

[89/143] [From passage: Postcards from 100 Boots]
Q5: Which of the choices provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[90/143] [From passage: Which Glove Do You Like Best?]
Q5: The writer uses the phrase “Okay, fine” in line 18 to:...
  -> Classifications: ['Line reading', 'Overarching purpose']

[91/143] [From passage: Connie “The Hawk” Hawkins]
Q5: In the third paragraph (lines 29-39), the passage transitions from a brief sketc...
  -> Classifications: ['Line reading', 'Overarching purpose']

[92/143] [From passage: Poet, Playwright, and... Spy?]
Q5: As used in line 50, the word “rank” most nearly means:...
  -> Classifications: ['Word-in-context']

[93/143] [From passage: Fund the Metro!]
Q5: Which choice provides the best evidence for the question above?...
  -> Classifications: ['Use of evidence']

[94/143] [From passage: Phrenology]
Q5: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[95/143] [From passage: Civic Engagement]
Q5: As used in line 48, “sway” most nearly means:...
  -> Classifications: ['Word-in-context']

[96/143] [From passage: The Creation and Destruction of the Globe]
Q6: Which of the following choices provides the best evidence for the previous answe...
  -> Classifications: ['Use of evidence']

[97/143] [From passage: Phrenology]
Q6: According to the passage, contemporary science:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[98/143] [From passage: “Pistol” Pete Maravich]
Q6: Pete Maravich:...
  -> Classifications: ['Line reading', 'Use of evidence']

[99/143] [From passage: Civic Engagement]
Q6: The author of Passage 2 characterizes voting as:...
  -> Classifications: ['Overarching purpose']

[100/143] [From passage: Let Sleeping Children Lie]
Q6: The purpose of the fifth paragraph (lines 45-52) is to:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[101/143] [From passage: The Longshoreman Philosopher]
Q6: The final paragraph (lines 38-49) relates that:...
  -> Classifications: ['Line reading', 'Use of evidence']

[102/143] [From passage: Am I a novelist?]
Q6: What is the point of the rhetorical questions posed in lines 42-49?...
  -> Classifications: ['Overarching purpose']

[103/143] [From passage: Which Glove Do You Like Best?]
Q6: As used in line 33, “comfortable” most nearly means:...
  -> Classifications: ['Word-in-context']

[104/143] [From passage: Connie “The Hawk” Hawkins]
Q6: As it’s used in line 50, the word 'summarily' most nearly means:...
  -> Classifications: ['Word-in-context']

[105/143] [From passage: The Blue Eyes/Brown Eyes Experiment]
Q6: Which of the choices provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[106/143] [From passage: Collegiate Athletics]
Q6: How would the author of Passage 1 likely respond to the anecdote presented in th...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[107/143] [From passage: Poet, Playwright, and... Spy?]
Q6: The author uses “supposed” (line 54), “swiftly” (line 57), and “totally random” ...
  -> Classifications: ['Word-in-context', 'Use of evidence']

[108/143] [From passage: Postcards from 100 Boots]
Q6: Starting with the third paragraph (lines 17-31) the passage transitions from:...
  -> No classifications matched

[109/143] [From passage: The Stanford Prison Experiment]
Q6: In the sixth paragraph (lines 45-49), the passage transitions from:...
  -> Classifications: ['Line reading']

[110/143] [From passage: The Stanford Prison Experiment]
Q7: Why was the Stanford Prison Experiment finally called off?...
  -> Classifications: ['Use of evidence']

[111/143] [From passage: Collegiate Athletics]
Q7: What is the relationship between Passage 1 and 2?...
  -> Classifications: ['Overarching purpose']

[112/143] [From passage: Postcards from 100 Boots]
Q7: The title of Carving a Traditional Sculpture is ironic because:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[113/143] [From passage: Civic Engagement]
Q7: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[114/143] [From passage: “Pistol” Pete Maravich]
Q7: As it’s used in line 44, the word “seemingly” most nearly means:...
  -> Classifications: ['Word-in-context']

[115/143] [From passage: Connie “The Hawk” Hawkins]
Q7: Which of the following is the most effective piece of evidence supporting Hawkin...
  -> Classifications: ['Use of evidence']

[116/143] [From passage: Which Glove Do You Like Best?]
Q7: According to the author, participants misattributed the reasons behind their glo...
  -> Classifications: ['Use of evidence']

[117/143] [From passage: Collegiate Athletics]
Q8: How would the author of Passage 2 likely respond to the suggestions made in line...
  -> Classifications: ['Use of evidence']

[118/143] [From passage: Civic Engagement]
Q8: In the context of Passage 2, the purpose of lines 65-75 (“If… decision.”) is to:...
  -> Classifications: ['Overarching purpose']

[119/143] [From passage: “Pistol” Pete Maravich]
Q8: The author of this passage would most likely agree with which of the following s...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[120/143] [From passage: The Stanford Prison Experiment]
Q8: What is the difference between a situational attribute and a dispositional one?...
  -> No classifications matched

[121/143] [From passage: Connie “The Hawk” Hawkins]
Q8: Why did the NBA eventually let Connie Hawkins into the league?...
  -> No classifications matched

[122/143] [From passage: Which Glove Do You Like Best?]
Q8: Which choice provides the best evidence for the answer to the previous question?...
  -> Classifications: ['Use of evidence']

[123/143] [From passage: Postcards from 100 Boots]
Q8: As used in line 40, “pointed” most nearly means:...
  -> Classifications: ['Word-in-context']

[124/143] [From passage: Connie “The Hawk” Hawkins]
Q9: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[125/143] [From passage: “Pistol” Pete Maravich]
Q9: Which lines provide the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[126/143] [From passage: Which Glove Do You Like Best?]
Q9: Which of the following would constitute a second order, introspective thought?...
  -> No classifications matched

[127/143] [From passage: Collegiate Athletics]
Q9: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[128/143] [From passage: The Stanford Prison Experiment]
Q9: Which of the choices provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[129/143] [From passage: Postcards from 100 Boots]
Q9: How frequently did Antin send “postcards” from the 100 boots?...
  -> Classifications: ['Line reading', 'Use of evidence']

[130/143] [From passage: Civic Engagement]
Q9: How would the author of Passage 2 most likely respond to the information present...
  -> Classifications: ['Overarching purpose']

[131/143] [From passage: Which Glove Do You Like Best?]
Q10: The author reacts to the findings in the study with:...
  -> Classifications: ['Line reading', 'Use of evidence']

[132/143] [From passage: Postcards from 100 Boots]
Q10: As used in line 76, “compelling” most nearly means:...
  -> Classifications: ['Word-in-context']

[133/143] [From passage: Civic Engagement]
Q10: What is the relationship between Passage 1 and Passage 2?...
  -> No classifications matched

[134/143] [From passage: Collegiate Athletics]
Q10: The final paragraph of Passage 2 (lines 77-88) serves to:...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[135/143] [From passage: The Stanford Prison Experiment]
Q10: According to the passage, the process of deindividuation is:...
  -> Classifications: ['Use of evidence']

[136/143] [From passage: Connie “The Hawk” Hawkins]
Q10: As they are presented in the passage, the ABA and ABL were:...
  -> Classifications: ['Line reading', 'Use of evidence']

[137/143] [From passage: Connie “The Hawk” Hawkins]
Q11: The main purpose of the final paragraph (lines 85-93) is to:...
  -> Classifications: ['Overarching purpose']

[138/143] [From passage: Collegiate Athletics]
Q11: How would the author of Passage 2 most likely respond to the information present...
  -> Classifications: ['Overarching purpose', 'Use of evidence']

[139/143] [From passage: Postcards from 100 Boots]
Q11: The main purpose of the final paragraph (lines 76-84) is to:...
  -> Classifications: ['Overarching purpose']

[140/143] [From passage: Civic Engagement]
Q11: What is one point that the authors of Passage 1 and 2 agree on?...
  -> Classifications: ['Use of evidence']

[141/143] [From passage: Which Glove Do You Like Best?]
Q11: The main point of the final paragraph (lines 57-73) is to:...
  -> Classifications: ['Overarching purpose']

[142/143] [From passage: The Stanford Prison Experiment]
Q11: Which choice provides the best evidence for the previous answer?...
  -> Classifications: ['Use of evidence']

[143/143] [From passage: Collegiate Athletics]
Q12: The authors of both passages agree that:...
  -> Classifications: ['Use of evidence']

Passage Questions: Classified 130
rishi@Mac satlingo_backend % 
