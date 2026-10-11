from io import BytesIO

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from world_cities import (
    CITIES,
    City,
    MAX_LEGS,
    MIN_LEGS,
    build_route,
    route_distance_km,
)


def format_stops(route):
    """Return the ordered itinerary as a human-readable string."""
    stops = [f"1. Start: {route[0].label}"]
    stops.extend(
        f"{index}. {city.label}"
        for index, city in enumerate(route[1:-1], start=2)
    )
    stops.append(f"{len(route)}. Return: {route[-1].label}")
    return "\n".join(stops)


def route_line_coordinates(route):
    longitudes = []
    latitudes = []
    for first, second in zip(route, route[1:]):
        longitude_delta = (second.longitude - first.longitude + 180) % 360 - 180
        adjusted_second_longitude = first.longitude + longitude_delta

        if adjusted_second_longitude > 180 or adjusted_second_longitude < -180:
            boundary_longitude = 180 if adjusted_second_longitude > 180 else -180
            fraction = (boundary_longitude - first.longitude) / (
                adjusted_second_longitude - first.longitude
            )
            boundary_latitude = first.latitude + fraction * (
                second.latitude - first.latitude
            )
            longitudes.extend(
                (
                    first.longitude,
                    boundary_longitude,
                    None,
                    -boundary_longitude,
                    second.longitude,
                    None,
                )
            )
            latitudes.extend(
                (
                    first.latitude,
                    boundary_latitude,
                    None,
                    boundary_latitude,
                    second.latitude,
                    None,
                )
            )
            continue

        longitudes.extend((first.longitude, second.longitude, None))
        latitudes.extend((first.latitude, second.latitude, None))
    return longitudes, latitudes


def make_route_figure(route):
    longitudes, latitudes = route_line_coordinates(route)
    stops = route[:-1]
    figure = go.Figure()
    figure.add_trace(
        go.Scattergeo(
            lon=longitudes,
            lat=latitudes,
            mode="lines",
            line={"width": 2, "color": "#0f766e"},
            hoverinfo="skip",
            name="Route",
        )
    )
    figure.add_trace(
        go.Scattergeo(
            lon=[city.longitude for city in stops],
            lat=[city.latitude for city in stops],
            mode="markers+text",
            text=[str(index) for index in range(1, len(stops) + 1)],
            textposition="top center",
            marker={"size": 9, "color": "#ea580c"},
            customdata=[city.label for city in stops],
            hovertemplate="%{customdata}<extra></extra>",
            name="Stops",
        )
    )
    figure.update_layout(
        template="plotly_white",
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        showlegend=False,
        geo={
            "projection_type": "natural earth",
            "showland": True,
            "landcolor": "#e8ede9",
            "showocean": True,
            "oceancolor": "#eaf4f8",
            "showcountries": True,
            "countrycolor": "#cbd5e1",
            "lataxis": {"showgrid": True, "gridcolor": "#dbe4e8"},
            "lonaxis": {"showgrid": True, "gridcolor": "#dbe4e8"},
        },
    )
    return figure


def create_route_pdf(route):
    figure_png = make_route_figure(route).to_image(format="png", width=1400, height=800)
    pdf_buffer = BytesIO()
    page_width, page_height = letter
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf.setTitle("Around-the-world route")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(42, page_height - 42, "Around-the-world route")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        42,
        page_height - 60,
        f"Total distance: {route_distance_km(route):,.0f} km",
    )
    pdf.drawImage(
        ImageReader(BytesIO(figure_png)),
        38,
        page_height - 330,
        width=page_width * 0.58,
        height=210,
        preserveAspectRatio=True,
        anchor="c",
    )
    list_x = page_width * 0.62
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(list_x, page_height - 92, "Stops")
    pdf.setFont("Helvetica", 7.5)
    y = page_height - 108
    for stop in format_stops(route).splitlines():
        for line in simpleSplit(stop, "Helvetica", 7.5, page_width - list_x - 36):
            pdf.drawString(list_x, y, line)
            y -= 9

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(42, 402, "Family history activities")
    margin = 42
    column_gap = 24
    column_width = (page_width - 2 * margin - column_gap) / 2
    columns = (
        (margin, family_history_activities[:4]),
        (margin + column_width + column_gap, family_history_activities[4:]),
    )
    for column_x, sections in columns:
        y = 382
        for title, activities in sections:
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(column_x, y, title)
            y -= 12
            pdf.setFont("Helvetica", 7.5)
            for activity in activities:
                lines = simpleSplit(
                    f"- {activity}", "Helvetica", 7.5, column_width - 8
                )
                for line in lines:
                    pdf.drawString(column_x + 8, y, line)
                    y -= 9
            y -= 5

    pdf.save()
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


app = Dash(__name__)
app.title = "Around the World Route Planner"

default_city = next(city for city in CITIES if city.name == "London")
family_history_activities = [
    (
        "Family Tree Work",
        [
            "Add ancestors, relatives, and descendants to the Family Tree.",
            "Correct names, dates, places, and relationships.",
            "Merge duplicate records.",
            "Add photos, stories, documents, and audio recordings.",
            "Review and verify information submitted by others.",
        ],
    ),
    (
        "Temple and Ordinance Work",
        [
            "Find ancestors who need temple ordinances.",
            "Reserve temple ordinances for yourself.",
            "Share ordinance opportunities with family members or the temple system.",
            "Print temple cards or use FamilySearch's mobile temple features where available.",
        ],
    ),
    (
        "Historical Record Research",
        [
            "Attach records to ancestors in the Family Tree.",
            "Compare conflicting records to improve accuracy.",
            "Discover new relatives through indexed documents.",
        ],
    ),
    (
        "Indexing and AI-Assisted Projects",
        [
            "Volunteer to index historical records so they become searchable.",
            "Participate in reviewing AI-generated record extractions.",
            "Help improve record quality through validation projects.",
        ],
    ),
    (
        "Family Discovery Activities",
        [
            'Use "Relatives Around Me" to find connections with nearby Church members.',
            "Explore family lines with fan charts and relationship tools.",
            "Discover famous or notable relatives.",
            'Use "View My Relationship" to see how you are connected to ancestors or living relatives.',
        ],
    ),
    (
        "Memories and Preservation",
        [
            "Upload family photos.",
            "Record and preserve family stories.",
            "Digitize old documents.",
            "Create lasting archives of family history materials.",
        ],
    ),
    (
        "Learning and Service",
        [
            "Complete FamilySearch learning courses.",
            "Attend FamilySearch webinars and training events.",
            "Help ward or stake members with family history research.",
            "Serve as a family history consultant.",
        ],
    ),
    (
        "Youth and Family Activities",
        [
            "Prepare names for youth temple trips.",
            "Participate in family history challenges.",
            "Create ancestor story presentations.",
            "Interview living relatives and preserve their histories.",
        ],
    ),
]

app.layout = html.Main(
    [
        html.H1("Around-the-world route planner"),
        html.P(
            "Choose a starting city and the number of route legs. "
            "Stops are selected from major cities at evenly spaced longitudes."
        ),
        html.Div(
            [
                html.Label("Starting location", htmlFor="start-city"),
                dcc.Dropdown(
                    id="start-city",
                    options=[
                        {"label": city.label, "value": city.name}
                        for city in sorted(CITIES, key=lambda city: city.label)
                    ],
                    value=default_city.name,
                    clearable=False,
                ),
                html.Label(
                    "Route legs (including the return leg)", htmlFor="leg-count"
                ),
                dcc.Slider(
                    id="leg-count",
                    min=MIN_LEGS,
                    max=MAX_LEGS,
                    step=1,
                    value=8,
                    marks={count: str(count) for count in range(MIN_LEGS, MAX_LEGS + 1, 2)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
            ],
            style={
                "maxWidth": "700px",
                "display": "grid",
                "gap": "8px",
                "marginBottom": "12px",
            },
        ),
        html.Div(
            [
                dcc.Graph(
                    id="route-map",
                    style={"height": "40vh", "minHeight": "300px"},
                    config={"displayModeBar": False},
                ),
                html.Section(
                    [
                        html.H2("Stops", style={"marginTop": 0}),
                        html.Pre(
                            id="stop-list",
                            style={
                                "whiteSpace": "pre-wrap",
                                "maxHeight": "36vh",
                                "overflowY": "auto",
                                "margin": 0,
                            },
                        ),
                    ],
                    className="stop-list-panel",
                    style={"padding": "12px 8px"},
                ),
            ],
            className="route-layout",
        ),
        html.Button("Download route as PDF", id="download-button", n_clicks=0),
        html.Div(id="download-error", role="alert", style={"color": "#b91c1c"}),
        html.Section(
            [
                html.H2("Family history activities"),
                html.Div(
                    [
                        html.Section(
                            [
                                html.H3(title),
                                html.Ul([html.Li(activity) for activity in activities]),
                            ],
                            className="activity-card",
                        )
                        for title, activities in family_history_activities
                    ],
                    className="activity-grid",
                ),
            ],
            className="activities-section",
        ),
        dcc.Store(id="route-data"),
        dcc.Download(id="route-download"),
    ],
    style={
        "maxWidth": "1200px",
        "margin": "0 auto",
        "padding": "24px",
        "fontFamily": "Arial, sans-serif",
    },
)


@app.callback(
    Output("route-map", "figure"),
    Output("stop-list", "children"),
    Output("route-data", "data"),
    Input("start-city", "value"),
    Input("leg-count", "value"),
)
def update_route(start_name, leg_count):
    route = build_route(start_name, leg_count)
    route_data = [
        {
            "name": city.name,
            "country": city.country,
            "latitude": city.latitude,
            "longitude": city.longitude,
        }
        for city in route
    ]
    return make_route_figure(route), format_stops(route), route_data


@app.callback(
    Output("route-download", "data"),
    Output("download-error", "children"),
    Input("download-button", "n_clicks"),
    State("route-data", "data"),
    prevent_initial_call=True,
)
def download_route(_n_clicks, route_data):
    if not _n_clicks or not route_data:
        return None, ""
    route = [City(**city) for city in route_data]
    try:
        pdf_bytes = create_route_pdf(route)
    except Exception as error:
        return None, f"Could not create the PDF: {error}"
    return dcc.send_bytes(pdf_bytes, "around-the-world-route.pdf"), ""


if __name__ == "__main__":
    app.run(debug=True)
