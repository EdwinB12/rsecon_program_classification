#  Aim

The job is to find all the talks given at the RSECon conference and classify them based on the type of event they belong to. This should be done by reading the abstract. Each talk should be classified into one of the following categories:

1. Research software : A talk about how software was used to answer a research question. It is more research focused than software focused.

2. Software Skill : A talk about how to use a piece of software. This talk is more software focused than research focused. It can be about a specific software package, or a general skill like version control, testing, etc.

3. Infrastructure : A talk about the infrastructure that supports research software. This can be about high performance computing, cloud computing, data storage, etc. It can also be about the tools and processes that support the development and maintenance of research software, such as continuous integration, code review, etc. There is some overlap between this category and the software skill category, but the focus of this category is more on the infrastructure and tools that support research software, rather than the software itself.

4. Management/Processes :  Talks about the management and processes that support research software. This can be about project management, software development methodologies, open source software development.

5. People/Community :  Talks about the people and community that support research software. This can be about diversity and inclusion in research software, career development for research software engineers, community building, etc.

6. Other/Not sure :  Talks that do not fit into any of the above categories or talks that are not clear enough to classify.

## Output

The output should consists of three things:

1. A results.csv file
2. A copy of all the .md files in the top level of the repository when it was run.

The results.csv file is a csv file in the following format:

Title, link to abstract, category, uncertain (True/False)

For each unique run of the program, create a sub folder in the output folder with the name of the run and preappend it with a timestamp. For example, if the program is run on 2024-06-01 at 12:00:00 and the run is named "run1", the output folder will be named "2024-06-01_12-00-00_run1". This will help in organizing the outputs of different runs and make it easier to track the results.


## Other rules

Some other rules:

1. Only look at events in the programme that are talks or presentations. Do not look at workshops, social events, plenary talks, satellite events or birds of a feather sessions.
2. Don't include names of anybody in the output.
3. If uncertain about the category it was placed in, mark it as uncertain.
4. The csv file should be named "results.csv" and placed in the output folder for each run.
5. STOP AFTER 5 TALKS. This is to make sure the program is working correctly before running it on the entire dataset. After 5 talks, the program should stop and output the results.csv file and the .md files in the output folder.

