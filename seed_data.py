"""Dataset loaded into the database on first start.

Company criteria are INDICATIVE values for this project, based on typical campus-hiring
notices. Real criteria change every year, so students must check each company's
official notice. Admins can edit or add companies from the Placement cell dashboard.
"""
from sqlalchemy import inspect, text

import models

ALL, TECH = "ALL", "CSE,IT,ECE"
COMPANY_COLS = ("name", "role", "domain", "ctc_lpa", "min_cgpa", "min_tenth", "min_twelfth",
                "max_backlogs", "branches", "min_aptitude", "min_coding", "min_dsa", "min_sql",
                "internship_req")
COMPANIES = [
    ("TCS", "Ninja", "IT Services", 3.6, 6.0, 60, 60, 1, ALL, 50, 35, 30, 30, 0),
    ("TCS", "Digital", "IT Services", 7.0, 6.5, 60, 60, 0, ALL, 65, 55, 50, 40, 0),
    ("Infosys", "Systems Engineer", "IT Services", 3.6, 6.0, 60, 60, 0, ALL, 50, 35, 30, 30, 0),
    ("Infosys", "Specialist Programmer", "Software Development", 9.5, 7.0, 60, 60, 0, TECH, 60, 70, 65, 50, 0),
    ("Wipro", "Project Engineer", "IT Services", 3.5, 6.0, 60, 60, 0, ALL, 50, 35, 30, 30, 0),
    ("HCLTech", "Graduate Engineer Trainee", "IT Services", 4.0, 6.0, 60, 60, 1, ALL, 50, 40, 35, 30, 0),
    ("Cognizant", "Programmer Analyst Trainee", "IT Services", 4.0, 6.0, 60, 60, 0, ALL, 55, 40, 35, 35, 0),
    ("Cognizant", "GenC Next", "Software Development", 6.75, 6.5, 60, 60, 0, TECH, 60, 55, 50, 45, 0),
    ("Accenture", "Associate Software Engineer", "IT Services", 4.6, 6.0, 60, 60, 1, ALL, 55, 40, 35, 35, 0),
    ("Capgemini", "Analyst", "IT Services", 4.0, 6.0, 60, 60, 1, ALL, 50, 40, 35, 30, 0),
    ("Tech Mahindra", "Associate Software Engineer", "IT Services", 3.5, 6.0, 55, 55, 2, ALL, 45, 30, 25, 25, 0),
    ("LTIMindtree", "Graduate Engineer Trainee", "IT Services", 4.0, 6.0, 60, 60, 0, ALL, 50, 40, 35, 30, 0),
    ("Persistent Systems", "Software Engineer", "Software Development", 5.0, 6.5, 60, 60, 0, "CSE,IT,ECE,EEE", 55, 55, 50, 45, 0),
    ("Zoho", "Software Developer", "Software Development", 6.0, 5.0, 0, 0, 3, ALL, 50, 70, 65, 40, 0),
    ("Paytm", "Software Engineer", "Software Development", 12.0, 7.0, 60, 60, 0, TECH, 60, 70, 65, 50, 0),
    ("Amazon", "SDE-1", "Software Development", 20.0, 7.0, 60, 60, 0, TECH, 65, 80, 80, 60, 1),
    ("Flipkart", "SDE-1", "Software Development", 24.0, 7.0, 60, 60, 0, TECH, 65, 80, 80, 60, 1),
    ("Microsoft", "Software Engineer", "Software Development", 30.0, 7.5, 70, 70, 0, TECH, 70, 85, 85, 65, 1),
    ("Deloitte", "Analyst (USI)", "Consulting and Business", 7.0, 6.5, 60, 60, 0, ALL, 65, 45, 40, 45, 0),
    ("LatentView Analytics", "Data Analyst", "Data and Analytics", 6.0, 6.5, 60, 60, 0, ALL, 65, 45, 40, 65, 1),
]

# skill, title, platform, url, level, note
RESOURCES = [
    ("aptitude", "Aptitude questions by topic", "IndiaBix", "https://www.indiabix.com/aptitude/questions-and-answers/", "Beginner", "Do 20 questions a day, one topic at a time."),
    ("aptitude", "Company-wise aptitude practice", "PrepInsta", "https://prepinsta.com/", "Intermediate", "Take a timed mock test every weekend."),
    ("aptitude", "Quantitative and reasoning practice", "GeeksforGeeks", "https://www.geeksforgeeks.org/", "Intermediate", "Focus on percentages, ratios, time and work."),
    ("coding", "Python and problem-solving practice", "HackerRank", "https://www.hackerrank.com/domains/python", "Beginner", "Finish the easy set, then start medium problems."),
    ("coding", "Interview coding problems", "LeetCode", "https://leetcode.com/problemset/", "Intermediate", "Solve 3 problems a week and review the solutions."),
    ("coding", "Practice problems and contests", "CodeChef", "https://www.codechef.com/practice", "Intermediate", "Join one monthly contest for speed."),
    ("dsa", "DSA tutorials and articles", "GeeksforGeeks", "https://www.geeksforgeeks.org/", "Beginner", "Cover arrays, strings, linked lists, stacks and queues first."),
    ("dsa", "Structured DSA roadmap", "takeuforward", "https://takeuforward.org/", "Intermediate", "Follow the sheet in order, topic by topic."),
    ("dsa", "Pattern-based DSA roadmap", "NeetCode", "https://neetcode.io/roadmap", "Intermediate", "Learn trees, graphs and dynamic programming patterns."),
    ("sql_score", "Interactive SQL lessons", "SQLZoo", "https://sqlzoo.net/", "Beginner", "Practise SELECT, joins and GROUP BY."),
    ("sql_score", "SQL practice problems", "HackerRank SQL", "https://www.hackerrank.com/domains/sql", "Intermediate", "Finish the basic and advanced select sets."),
    ("sql_score", "SQL reference and exercises", "W3Schools", "https://www.w3schools.com/sql/", "Beginner", "Revise constraints, keys and subqueries."),
    ("communication", "Improve spoken English", "BBC Learning English", "https://www.bbc.co.uk/learningenglish", "Beginner", "15 minutes of listening and speaking daily."),
    ("communication", "Public speaking practice", "Toastmasters", "https://www.toastmasters.org/", "Intermediate", "Join a club or practise with friends."),
    ("communication", "Record and review mock HR answers", "Self practice", "", "Beginner", "Answer 'Tell me about yourself' on video and improve it."),
    ("internship", "Internships for students", "Internshala", "https://internshala.com/", "Beginner", "Apply to 5 internships each week."),
    ("internship", "Government internship portal", "AICTE Internship Portal", "https://internship.aicte-india.org/", "Beginner", "Create a profile and apply early."),
    ("internship", "Virtual job simulations", "Forage", "https://www.theforage.com/", "Beginner", "Complete one simulation and add it to your resume."),
    ("certification", "Free university-level courses", "NPTEL", "https://nptel.ac.in/", "Beginner", "Pick a course in your domain and sit the exam."),
    ("certification", "Cloud Practitioner certification", "AWS", "https://aws.amazon.com/certification/certified-cloud-practitioner/", "Beginner", "A well-known entry-level cloud certificate."),
    ("certification", "Azure Fundamentals certification", "Microsoft Learn", "https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/", "Beginner", "Free learning path, paid exam."),
]

# category, question, options, correct option index, explanation
QUESTIONS = [
    ("aptitude", "A train 120 m long passes a pole in 6 seconds. Its speed in km/h is?", ["54", "72", "60", "80"], 1, "120 / 6 = 20 m/s, and 20 x 3.6 = 72 km/h."),
    ("aptitude", "If 20% of a number is 45, the number is?", ["180", "225", "200", "250"], 1, "45 / 0.20 = 225."),
    ("aptitude", "A can finish a job in 12 days and B in 18 days. Together they finish in?", ["6 days", "7.2 days", "8 days", "9 days"], 1, "1/12 + 1/18 = 5/36 of the job per day, so 36/5 = 7.2 days."),
    ("aptitude", "Find the next number: 2, 6, 12, 20, 30, ?", ["40", "42", "44", "36"], 1, "The differences are 4, 6, 8, 10, so the next difference is 12 and 30 + 12 = 42."),
    ("aptitude", "The average of 5 numbers is 24. When one number is removed the average becomes 22. The removed number is?", ["28", "30", "32", "34"], 2, "Total 120. Remaining total 4 x 22 = 88. Removed number = 32."),
    ("aptitude", "An item costs Rs 800 and is sold at 25% profit. The selling price is?", ["Rs 960", "Rs 1000", "Rs 1020", "Rs 1050"], 1, "800 x 1.25 = 1000."),
    ("aptitude", "In a code, CAT is written as DBU. How is DOG written?", ["EPH", "DPH", "EOH", "FPI"], 0, "Each letter moves one step forward: D to E, O to P, G to H."),
    ("aptitude", "Simple interest on Rs 5000 at 8% per year for 3 years is?", ["Rs 1000", "Rs 1200", "Rs 1500", "Rs 1600"], 1, "5000 x 8 x 3 / 100 = 1200."),
    ("coding", "What does this print in Python? x = 5; y = 2; print(x // y)", ["2.5", "2", "3", "2.0"], 1, "// is floor division, so 5 // 2 = 2."),
    ("coding", "Which structure gives average O(1) lookup by key?", ["Linked list", "Hash table", "Unsorted array scan", "Skewed binary tree"], 1, "Hash tables compute the position directly from the key."),
    ("coding", "Which of these Python types is immutable?", ["list", "dict", "tuple", "set"], 2, "Tuples cannot be changed after creation."),
    ("coding", "A function that calls itself is using?", ["Iteration", "Recursion", "Polymorphism", "Encapsulation"], 1, "Recursion means a function calls itself with a smaller input."),
    ("coding", "What does len('placement') return in Python?", ["8", "9", "10", "7"], 1, "The word has 9 characters."),
    ("coding", "Bundling data with methods and restricting direct access to it is called?", ["Inheritance", "Polymorphism", "Encapsulation", "Overloading"], 2, "Encapsulation keeps data and the code that uses it together and protected."),
    ("dsa", "Time complexity of binary search on a sorted array of n items?", ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1, "Each step halves the search range."),
    ("dsa", "Which data structure follows LIFO order?", ["Queue", "Stack", "Heap", "Graph"], 1, "A stack removes the most recently added item first."),
    ("dsa", "Which traversal of a binary search tree gives sorted order?", ["Preorder", "Inorder", "Postorder", "Level order"], 1, "Inorder visits left, node, right, which is ascending for a BST."),
    ("dsa", "Worst-case time complexity of quicksort?", ["O(n log n)", "O(n)", "O(n^2)", "O(log n)"], 2, "A bad pivot choice leads to O(n^2)."),
    ("dsa", "Which algorithm finds shortest paths from one source with non-negative weights?", ["DFS", "Dijkstra's", "Kruskal's", "Prim's"], 1, "Dijkstra's algorithm is built for non-negative edge weights."),
    ("dsa", "How many edges does a tree with n nodes have?", ["n", "n + 1", "n - 1", "n - 2"], 2, "A tree is connected with no cycles, so it has n - 1 edges."),
    ("sql_score", "Which clause filters groups after GROUP BY?", ["WHERE", "HAVING", "ORDER BY", "LIMIT"], 1, "WHERE filters rows before grouping, HAVING filters groups after."),
    ("sql_score", "Which keyword removes duplicate rows from a result?", ["UNIQUE", "DISTINCT", "DIFFERENT", "REMOVE"], 1, "SELECT DISTINCT returns unique rows."),
    ("sql_score", "Which join returns all rows of the left table plus matches from the right?", ["INNER JOIN", "LEFT JOIN", "CROSS JOIN", "SELF JOIN"], 1, "LEFT JOIN keeps every left row, with NULL where there is no match."),
    ("sql_score", "Which constraint makes every value in a column different?", ["NOT NULL", "UNIQUE", "CHECK", "DEFAULT"], 1, "UNIQUE rejects duplicate values."),
    ("sql_score", "What does SELECT COUNT(*) FROM students; return?", ["Number of columns", "Number of rows", "Sum of values", "Highest value"], 1, "COUNT(*) counts rows."),
    ("sql_score", "Which command removes a table and its structure completely?", ["DELETE", "TRUNCATE", "DROP TABLE", "REMOVE"], 2, "DROP TABLE deletes the table itself."),
    ("communication", "Choose the correct sentence.", ["She don't like coffee.", "She doesn't like coffee.", "She not like coffee.", "She doesn't likes coffee."], 1, "With 'she', use 'doesn't' and the base verb 'like'."),
    ("communication", "In an interview you do not know the answer. The best response is to?", ["Guess confidently", "Say you don't know and stop", "Think aloud, share what you do know and how you would find out", "Change the topic"], 2, "Interviewers value your thinking process and honesty."),
    ("communication", "Which email subject line is most professional for a job application?", ["Hi", "Need job urgently!!!", "Application for Software Engineer Role - Asha Verma", "Please read"], 2, "It is specific, polite and tells the reader what the email is about."),
    ("communication", "In a group discussion, the best way to disagree is to?", ["Interrupt and correct them", "Stay silent", "Acknowledge their point, then add your view with a reason", "Raise your voice"], 2, "Respectful disagreement with reasons shows maturity."),
]


def ensure_columns(engine, Base):
    """Add columns that were introduced after the database was first created."""
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} "
                                      f"{col.type.compile(engine.dialect)}"))


def seed(SessionLocal):
    db = SessionLocal()
    try:
        if db.query(models.Company).filter(models.Company.role.isnot(None)).count() == 0:
            names = {c[0] for c in COMPANIES}
            db.query(models.Company).filter(models.Company.role.is_(None),
                                            models.Company.name.in_(names)).delete(synchronize_session=False)
            for row in COMPANIES:
                db.add(models.Company(**dict(zip(COMPANY_COLS, row))))
        if db.query(models.Resource).count() == 0:
            for skill, title, platform, url, level, note in RESOURCES:
                db.add(models.Resource(skill=skill, title=title, platform=platform,
                                       url=url, level=level, note=note))
        if db.query(models.Question).count() == 0:
            for cat, q, opts, ans, why in QUESTIONS:
                db.add(models.Question(category=cat, text=q, options="||".join(opts),
                                       answer=ans, explanation=why))
        db.commit()
    finally:
        db.close()


def setup(engine, Base, SessionLocal):
    ensure_columns(engine, Base)
    seed(SessionLocal)
