# FH-World

An around-the-world route planner built with Plotly Dash. It uses the major-city
catalogue and route selection logic in `world_cities.py`.

## Run the app

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open the local URL printed by Dash. Select a starting city and a leg count to
view the route and its ordered stops. The leg count includes the final return
leg to the starting city. Use **Download route as PDF** to export the map and
stop list together with the Family History Activities list on one page.
