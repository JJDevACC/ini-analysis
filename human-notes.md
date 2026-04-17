## [I&I] Flow Data to ADS Sliicer Automation

### Description and Goal of this Sub Project
Currently, a Water Wastewater Engineer has to use the PI Web API, accessed using R code, to pull flow data from a PI Point and write it to a CSV file.  The CSV file has to be in a very specific format.  An example of this CSV file is available at C:\repository\local\ini-analysis\data-to-sliicer\examples\WES8617.csv.  The Water Wastewater Engineer then takes that CSV file and manually uploads it to the ADS Prism   
This sub project is trying to accomplish the following:
1.  Use the example R code in the below section and convert that to equivalent Python code that will extract the data in the exact same way.
2.  Once the data is extracted using Python from item 1, they Python code should then create a CSV file in the exact same format as the example CSV file at C:\repository\local\ini-analysis\data-to-sliicer\examples\WES8617.csv.  
3.  Determine a method of Posting or automating the data into the ADS Sliicer app.  Preferably by using the API endpoint in the swagger UI specification, at https://api.adsprism.com/swagger/index.html, or by trying to automate the CSV upload.

### Example R Code From Craig to Get Correct Data From PI Point
library(piwebapi)
 
tags <- c("wwl:south:wes8617b_realtmmetflo")
 
tmp <- piwebapi::get_sampled_multi(tags, ymd(today())-days(5), ymd(today()))
 
tmp %>% 
  mutate(datehour=round_date(datetime, "1h")) %>% 
  group_by(datehour) %>% 
  summarize(q=mean(wwl.South.WES8617B_REALTMMETFLO, na.rm=TRUE))

### Folders for R Libraries Used In Conjunction with R Code for Making CSV File
C:\repository\local\ini-analysis\support\piwebapi

### PI Web API Version and Title
#### Product Title
PI Web API 2023 SP1 Patch 1

#### Product Version
1.19.1.28

#### PI Web API Reference Documentation as Markdown
C:\repository\references\pi-web-api\pi_web_api_reference_4-9-2026.md

### Proposed Process In Conjunction with AI/Kiro
1.  Need AI to read and understand the example R code (from the Water Wastewater Engineer) from above that represents a sample data pull using PI Web API.
2.  Need AI to read and understand the existing R PI Web API library (from the Water Wastewater Engineer) located at C:\repository\local\ini-analysis\support\piwebapi.
3.  Need AI to read and understand the PI Web API Documentation from AVEVA located at C:\repository\references\pi-web-api\pi_web_api_reference_4-9-2026.md.
4.  Need AI to read and understand the sample CSV file, located at C:\repository\local\ini-analysis\data-to-sliicer\examples\WES8617.csv, to see the current result of the R code that is manually uploaded into ADS Prism for the Sliicer application.
5.  After reading and understanding the context of the current process, we need to start with simple steps to reproduce this process using Python v3.12.  The first step is likely to be to produce the simplest Python code that will get the data from PI Web API in the proper timestep matching the WES8617.csv data.  This code should make use of an environment variable file so we can have a separate place to put the URL of our organizations PI Web API endpoint, credential name and password, etc.  This code should also make use of a .bat file so that the Python code can be ran with different passed parameters, such as PI Point name, start time, end time, calculation type (e.g. average vs. interpolated) without having to pass those each time into the command line to test running the Python code.  Other best practices for this level or development should be incorporated by the AI tool.

### Project Working Folder
All code and items for this section of the project shall be placed or used in the following folder, C:\repository\local\ini-analysis\data-to-sliicer.

### Sample PI Points to be used to Validate Example CSV files
wwl:east:bra10477b_realtmmetflo
wwl:south:wes8617b_realtmmetflo

## [I&I] AF Database Upload Automation

### Folders for R Libraries Used In Conjunction with R Code for Making the CSV PI Builder Upload File
C:\repository\local\ini-analysis\support\gisimport
C:\repository\local\ini-analysis\support\piwebapi

### Azure DevOps Repo
https://dev.azure.com/jea-org/WWSP/

