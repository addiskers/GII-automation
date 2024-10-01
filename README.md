# Flask Web App with Selenium

This Flask application scrapes reports from a given list of URLs using Selenium, processes the scraped data, and generates an Excel file containing the results. It uses `webdriver_manager` to manage ChromeDriver and runs in a headless mode for deployment on Render.

## Features

- Flask web interface to input URLs for scraping.
- Uses Selenium to navigate web pages and extract content.
- Generates a downloadable Excel file from the scraped data.
- Deployed on Render with a workaround for headless Chrome installation.

## Technologies Used

- **Flask**: Web framework to create a web interface for the application.
- **Selenium**: Used to automate browser actions and scrape web content.
- **BeautifulSoup**: For HTML parsing and extracting data from web pages.
- **OpenAI**: Integration with OpenAI API for language processing tasks.
- **OpenPyXL**: For generating Excel files from the scraped data.
- **webdriver_manager**: For managing ChromeDriver automatically.
- **Google Chrome**: Runs in headless mode for rendering pages.

---

## How to Set Up

### Prerequisites

1. **Python 3.x** installed.
2. **Render account** to deploy the application.
3. A `.env` file with the `OPENAI_API_KEY` for OpenAI API usage.

### Install Dependencies

First, clone the repository:

```bash
git clone https://github.com/addiskers/GII-automation.git
cd your-repo


Then install the required Python dependencies:

```bash
pip install -r requirements.txt
```

### Running Locally

To run the app locally, make sure to have Chrome installed and then run the application:

```bash
python app.py
```

The application will be available at `http://localhost:5000/`.

### Deploying on Render

To deploy on Render, you'll need to ensure that Chrome and ChromeDriver are installed in the Render environment. We've included a script called `render-build.sh` to handle this.

### Important Selenium Path Issue on Render

When deploying on **Render**, you'll run into an issue where **Selenium** cannot find. This is because Render doesn't have Chrome installed by default, and Selenium needs to know the path in the Render environment.

To solve this:

1. **Chrome Installation**: You need to install Chrome manually during the build process using a shell script. The `render-build.sh` script downloads and installs Chrome into a custom path on Render (`/opt/render/project/.render/chrome`).
   
2. **Modify PATH in Start Command**: In the Render dashboard, set the **Start Command** to include the correct Chrome binary path:

   ```bash
   export PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome" && python app.py
   ```


### Render Build Command

In the Render dashboard, set the **Build Command** to run the `render-build.sh` script:

```bash
./render-build.sh
```

This script will install Chrome and all the required Python dependencies.

### Render Start Command

Set the **Start Command** in Render as follows:

```bash
export PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome" && python app.py
```

This ensures that the Chrome binary is in the PATH, allowing Selenium to locate and use it.

---

## Example Workflow

1. Navigate to the homepage of the application.
2. Paste a list of URLs you want to scrape in the text area.
3. Click **Generate Excel**.
4. The app will scrape the content, generate an Excel file, and prompt you to download it.

---

## Troubleshooting

### Common Issues on Render

- **Selenium Can't Find Chrome**: Ensure that Chrome is installed and added to the PATH in your Render start command.
- **Timeouts**: Make sure your web scraping logic waits for elements to load before attempting to extract data (e.g., using `WebDriverWait`).

### Solutions

- The `render-build.sh` script handles Chrome installation.
- Use `webdriver_manager` to install ChromeDriver automatically and keep it updated.

---

## License

This project is open-source and available under the MIT License.

---

## render-build.sh Script

Here is the content for the `render-build.sh` script that installs Chrome:

```bash
#!/usr/bin/env bash
# Exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
  cd $HOME/project/src  # Make sure we return to where we were
else
  echo "...Using Chrome from cache"
fi

# Add your build commands here (like pip install)
pip install -r requirements.txt
```

---

This README provides all the necessary information to set up, run, and deploy your Flask web scraper using Selenium and Chrome on Render. If you encounter any issues, follow the **Troubleshooting** section or adjust the **Selenium Chrome Setup** as needed.
```

### Next Steps:
1. Add this as your `README.md` file in your project repository.
2. Ensure the `render-build.sh` script is added to your project as described.
3. Follow the steps in the README for deployment and setup.

Let me know if you need further adjustments!
