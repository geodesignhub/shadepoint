from dashboard.extension import db

from shapely import Point as ShapelyPoint
from dashboard.nbsapi.models.naturebasedsolution import (
    TreeLocation,
)
from geoalchemy2.shape import from_shape

from geojson import FeatureCollection


class TreesDatabaseWriter:
    """
    A class to handle writing tree data to a database.
    Attributes:
        trees (FeatureCollection): A collection of tree features to be written to the database.
        location (str): The location associated with the tree data.
        session_id (str): A unique identifier for the session.
    Methods:
        write_trees_to_db():
            Writes the tree data to the database, including geometry and location information.
    """

    def __init__(self, trees: FeatureCollection, location: str, session_id: str):
        self.trees = trees
        self.location = location
        self.session_id = session_id

    def write_trees_to_database(self):
        """
        Writes tree data to the database.
        This method iterates over the features in the `trees` attribute, extracts
        their geometry, converts it into a Shapely Point, and then creates a
        `TreeLocation` object for each tree. The `TreeLocation` objects are added
        to the database session and committed to persist the data.
        Attributes:
            trees.features (list): A list of tree features, each containing geometry data.
            location (str): The location associated with the tree data.
            session_id (str): The session identifier for the current operation.
        Raises:
            Any exceptions raised by the database session operations.
        """

        for tree in self.trees.features:
            tree_geometry = tree.geometry
            shapely_point = ShapelyPoint(tree_geometry.coordinates)
            my_tree_location = from_shape(shapely_point)
            tree_location = TreeLocation(
                location=self.location,
                geometry=my_tree_location,
                session_id=self.session_id,
            )

            db.session.add(tree_location)

        db.session.commit()
