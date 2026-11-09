import os
import math
from datetime import datetime

from openpyxl import load_workbook


# =========================================================
# FILE PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

AIR_FILE = os.path.join(
    BASE_DIR,
    "Hermes_AI_Assignment_AIR_Rate_Sheet.xlsx"
)

OCEAN_FILE = os.path.join(
    BASE_DIR,
    "Hermes_AI_Assignment_OCEAN_Rate_Sheet.xlsx"
)


# =========================================================
# LOAD EXCEL SHEETS
# =========================================================

def load_sheet(file_path, sheet_name):

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Excel file not found: {file_path}"
        )

    workbook = load_workbook(
        file_path,
        data_only=True
    )

    if sheet_name not in workbook.sheetnames:
        raise ValueError(
            f"Sheet '{sheet_name}' not found "
            f"in {file_path}"
        )

    worksheet = workbook[sheet_name]

    rows = list(
        worksheet.iter_rows(
            values_only=True
        )
    )

    if not rows:
        return []

    headers = rows[0]

    records = []

    for row in rows[1:]:

        record = {}

        for index, header in enumerate(headers):

            if index < len(row):
                record[header] = row[index]
            else:
                record[header] = None

        records.append(record)

    return records


# =========================================================
# GET AIR RATES
# =========================================================

def get_air_rates():

    return load_sheet(
        AIR_FILE,
        "AIR_Rates"
    )


# =========================================================
# GET OCEAN RATES
# =========================================================

def get_ocean_rates():

    return load_sheet(
        OCEAN_FILE,
        "OCEAN_Rates"
    )


# =========================================================
# NORMALIZE TEXT
# =========================================================

def normalize_text(value):

    if value is None:
        return ""

    return str(value).strip().lower()


# =========================================================
# NORMALIZE LOCATION
# =========================================================

def normalize_location(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    # If the LLM gives:
    # Mumbai, India
    # Mumbai, Maharashtra, India
    #
    # keep only the city/locality:
    # Mumbai
    if "," in value:
        value = value.split(",")[0].strip()

    return value


# =========================================================
# NORMALIZE CONTAINER TYPE
# =========================================================

def normalize_container_type(value):

    if value is None:
        return None

    value = str(value).strip().upper()

    replacements = {
        "20 FEET": "20FT",
        "20 FOOT": "20FT",
        "20 FEET CONTAINER": "20FT",
        "20FT CONTAINER": "20FT",

        "40 FEET": "40FT",
        "40 FOOT": "40FT",
        "40 FEET CONTAINER": "40FT",
        "40FT CONTAINER": "40FT",

        "40 HC": "40HC",
        "40HC CONTAINER": "40HC"
    }

    return replacements.get(
        value,
        value
    )


# =========================================================
# PARSE VALIDITY
# =========================================================

def parse_validity(validity):

    if not validity:
        return None, None

    validity = str(validity).strip()

    parts = validity.split("to")

    if len(parts) != 2:
        return None, None

    start_text = parts[0].strip()
    end_text = parts[1].strip()

    try:

        start_date = datetime.strptime(
            start_text,
            "%d-%b-%Y"
        ).date()

        end_date = datetime.strptime(
            end_text,
            "%d-%b-%Y"
        ).date()

        return start_date, end_date

    except ValueError:

        return None, None


# =========================================================
# CHECK RATE VALIDITY
# =========================================================

def is_rate_valid(
    validity,
    shipment_date=None
):

    start_date, end_date = parse_validity(
        validity
    )

    if start_date is None or end_date is None:
        return True

    if shipment_date is None:
        return True

    return (
        start_date
        <= shipment_date
        <= end_date
    )


# =========================================================
# PARSE SHIPMENT DATE
# =========================================================

def parse_shipment_date(value):

    if not value:
        return None

    if hasattr(value, "date"):
        return value.date()

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%d %B %Y",
        "%d %b %Y"
    ]

    for date_format in formats:

        try:

            return datetime.strptime(
                value,
                date_format
            ).date()

        except ValueError:

            continue

    return None


# =========================================================
# COMMODITY MATCH
# =========================================================

def commodity_matches(
    commodity,
    commodity_notes
):

    if not commodity:
        return True

    if not commodity_notes:
        return True

    commodity = normalize_text(
        commodity
    )

    notes = normalize_text(
        commodity_notes
    )

    if commodity in notes:
        return True

    commodity_words = [
        word
        for word in commodity.split()
        if len(word) > 3
    ]

    if not commodity_words:
        return True

    return any(
        word in notes
        for word in commodity_words
    )


# =========================================================
# CALCULATE AIR CHARGEABLE WEIGHT
# =========================================================

def calculate_air_chargeable_weight(
    weight_kg,
    length_cm=None,
    width_cm=None,
    height_cm=None,
    pieces=None,
    volume_cbm=None
):

    if weight_kg is None:
        return None, None

    try:
        gross_weight = float(weight_kg)
    except (TypeError, ValueError):
        return None, None

    volumetric_weight = None

    # -----------------------------------------------------
    # OPTION 1: EXPLICIT CBM
    # -----------------------------------------------------

    if volume_cbm is not None:

        try:

            volume = float(volume_cbm)

            if volume > 0:
                volumetric_weight = (
                    volume * 1_000_000 / 6000
                )

        except (TypeError, ValueError):
            volumetric_weight = None

    # -----------------------------------------------------
    # OPTION 2: DIMENSIONS + PIECES
    # -----------------------------------------------------

    elif (
        length_cm is not None
        and width_cm is not None
        and height_cm is not None
        and pieces is not None
    ):

        try:

            length = float(length_cm)
            width = float(width_cm)
            height = float(height_cm)
            piece_count = float(pieces)

            if (
                length > 0
                and width > 0
                and height > 0
                and piece_count > 0
            ):

                volumetric_weight = (
                    length
                    * width
                    * height
                    * piece_count
                    / 6000
                )

        except (TypeError, ValueError):
            volumetric_weight = None

    # -----------------------------------------------------
    # CHARGEABLE WEIGHT
    # -----------------------------------------------------

    if volumetric_weight is not None:

        chargeable_weight = max(
            gross_weight,
            volumetric_weight
        )

    else:

        chargeable_weight = gross_weight

    chargeable_weight = math.ceil(
        chargeable_weight
    )

    return (
        chargeable_weight,
        volumetric_weight
    )


# =========================================================
# AIR RATE LOOKUP
# =========================================================

def find_air_rate(
    origin,
    destination,
    weight_kg,
    length_cm=None,
    width_cm=None,
    height_cm=None,
    pieces=None,
    volume_cbm=None,
    shipment_date=None,
    cargo_type=None
):

    rates = get_air_rates()

    # IMPORTANT:
    # Normalize city names so:
    # "Mumbai" == "Mumbai, India"
    # "Frankfurt" == "Frankfurt, Germany"
    origin = normalize_location(origin)
    destination = normalize_location(destination)

    (
        chargeable_weight,
        volumetric_weight
    ) = calculate_air_chargeable_weight(
        weight_kg=weight_kg,
        length_cm=length_cm,
        width_cm=width_cm,
        height_cm=height_cm,
        pieces=pieces,
        volume_cbm=volume_cbm
    )

    if chargeable_weight is None:

        return {
            "found": False,
            "match_type": "none",
            "mode": "air",
            "message": "Chargeable weight could not be calculated."
        }

    for rate in rates:

        if normalize_location(
            rate.get("Origin")
        ) != origin:
            continue

        if normalize_location(
            rate.get("Destination")
        ) != destination:
            continue

        min_weight = rate.get(
            "Min_Chargeable_KG"
        )

        max_weight = rate.get(
            "Max_Chargeable_KG"
        )

        if min_weight is None:
            continue

        if max_weight is None:
            continue

        if not (
            min_weight
            <= chargeable_weight
            <= max_weight
        ):
            continue

        if not is_rate_valid(
            rate.get("Validity"),
            shipment_date
        ):
            continue

        if not commodity_matches(
            cargo_type,
            rate.get("Commodity_Notes")
        ):
            continue

        rate_per_kg = rate.get(
            "Rate_Per_KG"
        )

        if rate_per_kg is None:
            continue

        total_price = (
            chargeable_weight
            * rate_per_kg
        )

        return {

            "found": True,

            "match_type": "exact",

            "mode": "air",

            "rate_id": rate.get(
                "Rate_ID"
            ),

            "origin": rate.get(
                "Origin"
            ),

            "destination": rate.get(
                "Destination"
            ),

            "currency": rate.get(
                "Currency"
            ),

            "rate_basis": rate.get(
                "Rate_Basis"
            ),

            "rate_per_kg": rate_per_kg,

            "gross_weight_kg": weight_kg,

            "volumetric_weight_kg": (
                round(volumetric_weight, 2)
                if volumetric_weight is not None
                else None
            ),

            "chargeable_weight_kg":
                chargeable_weight,

            "total_price":
                total_price,

            "transit_time":
                rate.get("Transit_Time"),

            "routing":
                rate.get("Routing"),

            "validity":
                rate.get("Validity"),

            "commodity_notes":
                rate.get("Commodity_Notes")
        }

    return {

        "found": False,

        "match_type": "none",

        "mode": "air",

        "origin": origin,

        "destination": destination,

        "chargeable_weight_kg":
            chargeable_weight,

        "volumetric_weight_kg":
            (
                round(volumetric_weight, 2)
                if volumetric_weight is not None
                else None
            ),

        "message":
            "No applicable air rate was found."
    }


# =========================================================
# CHECK OCEAN UNIT RANGE
# =========================================================

def ocean_units_are_valid(
    container_count,
    min_units,
    max_units
):

    if container_count is None:
        return False

    if min_units is not None:

        if container_count < min_units:
            return False

    if max_units is not None:

        if container_count > max_units:
            return False

    return True


# =========================================================
# OCEAN EXACT RATE
# =========================================================

def find_ocean_exact_rate(
    origin,
    destination,
    shipment_type,
    container_type,
    container_count=1,
    shipment_date=None,
    cargo_type=None
):

    rates = get_ocean_rates()

    origin = normalize_location(origin)
    destination = normalize_location(destination)
    shipment_type = normalize_text(shipment_type)

    container_type = normalize_container_type(
        container_type
    )

    for rate in rates:

        if normalize_location(
            rate.get("Origin")
        ) != origin:
            continue

        if normalize_location(
            rate.get("Destination")
        ) != destination:
            continue

        if normalize_text(
            rate.get("Shipment_Type")
        ) != shipment_type:
            continue

        rate_container_type = normalize_container_type(
            rate.get("Container_Type")
        )

        if rate_container_type != container_type:
            continue

        min_units = rate.get(
            "Min_Units"
        )

        max_units = rate.get(
            "Max_Units"
        )

        if not ocean_units_are_valid(
            container_count,
            min_units,
            max_units
        ):
            continue

        if not is_rate_valid(
            rate.get("Validity"),
            shipment_date
        ):
            continue

        if not commodity_matches(
            cargo_type,
            rate.get("Commodity_Notes")
        ):
            continue

        rate_per_unit = rate.get(
            "Rate_Per_Unit"
        )

        if rate_per_unit is None:
            continue

        total_price = (
            rate_per_unit
            * container_count
        )

        return {

            "found": True,

            "match_type": "exact",

            "mode": "ocean",

            "rate_id":
                rate.get("Rate_ID"),

            "origin":
                rate.get("Origin"),

            "destination":
                rate.get("Destination"),

            "shipment_type":
                rate.get("Shipment_Type"),

            "container_type":
                rate.get("Container_Type"),

            "container_count":
                container_count,

            "currency":
                rate.get("Currency"),

            "rate_basis":
                rate.get("Rate_Basis"),

            "rate_per_container":
                rate_per_unit,

            "min_units":
                min_units,

            "max_units":
                max_units,

            "total_price":
                total_price,

            "transit_time":
                rate.get("Transit_Time"),

            "routing":
                rate.get("Routing"),

            "validity":
                rate.get("Validity"),

            "commodity_notes":
                rate.get("Commodity_Notes")
        }

    return {

        "found": False,

        "match_type": "none",

        "mode": "ocean"
    }


# =========================================================
# OCEAN ALTERNATIVE RATE
# =========================================================

def find_ocean_alternative_rate(
    origin,
    destination,
    shipment_type,
    requested_container_type,
    container_count=1,
    shipment_date=None,
    cargo_type=None
):

    rates = get_ocean_rates()

    origin = normalize_location(origin)
    destination = normalize_location(destination)
    shipment_type = normalize_text(shipment_type)

    requested_container_type = normalize_container_type(
        requested_container_type
    )

    rejected_alternatives = []
    valid_alternatives = []

    for rate in rates:

        if normalize_location(
            rate.get("Origin")
        ) != origin:
            continue

        if normalize_location(
            rate.get("Destination")
        ) != destination:
            continue

        if normalize_text(
            rate.get("Shipment_Type")
        ) != shipment_type:
            continue

        rate_container_type = normalize_container_type(
            rate.get("Container_Type")
        )

        if rate_container_type == requested_container_type:
            continue

        min_units = rate.get(
            "Min_Units"
        )

        max_units = rate.get(
            "Max_Units"
        )

        if not is_rate_valid(
            rate.get("Validity"),
            shipment_date
        ):
            continue

        if not commodity_matches(
            cargo_type,
            rate.get("Commodity_Notes")
        ):
            continue

        rate_per_unit = rate.get(
            "Rate_Per_Unit"
        )

        if rate_per_unit is None:
            continue

        units_valid = ocean_units_are_valid(
            container_count,
            min_units,
            max_units
        )

        # -------------------------------------------------
        # ALTERNATIVE EXISTS BUT QUANTITY INVALID
        # -------------------------------------------------

        if not units_valid:

            rejected_alternatives.append({

                "container_type":
                    rate_container_type,

                "rate_id":
                    rate.get("Rate_ID"),

                "currency":
                    rate.get("Currency"),

                "rate_basis":
                    rate.get("Rate_Basis"),

                "rate_per_container":
                    rate_per_unit,

                "min_units":
                    min_units,

                "max_units":
                    max_units,

                "requested_units":
                    container_count,

                "reason":
                    "Requested container quantity "
                    "is outside the allowed "
                    "Min_Units and Max_Units range."
            })

            continue

        # -------------------------------------------------
        # VALID ALTERNATIVE
        # -------------------------------------------------

        total_price = (
            rate_per_unit
            * container_count
        )

        valid_alternatives.append({

            "found": True,

            "match_type":
                "alternative",

            "mode":
                "ocean",

            "requested_container_type":
                requested_container_type,

            "alternative_container_type":
                rate_container_type,

            "rate_id":
                rate.get("Rate_ID"),

            "origin":
                rate.get("Origin"),

            "destination":
                rate.get("Destination"),

            "shipment_type":
                rate.get("Shipment_Type"),

            "container_count":
                container_count,

            "currency":
                rate.get("Currency"),

            "rate_basis":
                rate.get("Rate_Basis"),

            "rate_per_container":
                rate_per_unit,

            "min_units":
                min_units,

            "max_units":
                max_units,

            "total_price":
                total_price,

            "transit_time":
                rate.get("Transit_Time"),

            "routing":
                rate.get("Routing"),

            "validity":
                rate.get("Validity"),

            "commodity_notes":
                rate.get("Commodity_Notes")
        })

    if valid_alternatives:

        return valid_alternatives[0]

    if rejected_alternatives:

        return {

            "found": False,

            "match_type":
                "alternative_quantity_exceeded",

            "mode":
                "ocean",

            "requested_container_type":
                requested_container_type,

            "requested_container_count":
                container_count,

            "rejected_alternatives":
                rejected_alternatives,

            "message":
                "An alternative container rate exists, "
                "but the requested container quantity "
                "is outside the applicable quantity range."
        }

    return {

        "found": False,

        "match_type":
            "none",

        "mode":
            "ocean"
    }


# =========================================================
# OCEAN LCL RATE
# =========================================================

def find_ocean_lcl_rate(
    origin,
    destination,
    volume_cbm,
    shipment_date=None,
    cargo_type=None
):

    rates = get_ocean_rates()

    origin = normalize_location(origin)
    destination = normalize_location(destination)

    try:
        volume = float(volume_cbm)
    except (TypeError, ValueError):
        return {
            "found": False,
            "match_type": "none",
            "mode": "ocean",
            "message": "Valid LCL volume in CBM is required."
        }

    # LCL minimum = 1 CBM
    billable_cbm = max(
        1.0,
        volume
    )

    billable_cbm = round(
        billable_cbm,
        2
    )

    for rate in rates:

        if normalize_location(
            rate.get("Origin")
        ) != origin:
            continue

        if normalize_location(
            rate.get("Destination")
        ) != destination:
            continue

        if normalize_text(
            rate.get("Shipment_Type")
        ) != "lcl":
            continue

        if not is_rate_valid(
            rate.get("Validity"),
            shipment_date
        ):
            continue

        if not commodity_matches(
            cargo_type,
            rate.get("Commodity_Notes")
        ):
            continue

        min_units = rate.get(
            "Min_Units"
        )

        max_units = rate.get(
            "Max_Units"
        )

        if min_units is not None:

            if billable_cbm < min_units:
                continue

        if max_units is not None:

            if billable_cbm > max_units:
                continue

        rate_per_unit = rate.get(
            "Rate_Per_Unit"
        )

        if rate_per_unit is None:
            continue

        total_price = round(
            billable_cbm
            * rate_per_unit,
            2
        )

        return {

            "found": True,

            "match_type":
                "exact",

            "mode":
                "ocean",

            "rate_id":
                rate.get("Rate_ID"),

            "origin":
                rate.get("Origin"),

            "destination":
                rate.get("Destination"),

            "shipment_type":
                "LCL",

            "container_type":
                "LCL",

            "volume_cbm":
                billable_cbm,

            "currency":
                rate.get("Currency"),

            "rate_basis":
                rate.get("Rate_Basis"),

            "rate_per_cbm":
                rate_per_unit,

            "total_price":
                total_price,

            "transit_time":
                rate.get("Transit_Time"),

            "routing":
                rate.get("Routing"),

            "validity":
                rate.get("Validity"),

            "commodity_notes":
                rate.get("Commodity_Notes")
        }

    return {

        "found": False,

        "match_type":
            "none",

        "mode":
            "ocean",

        "origin":
            origin,

        "destination":
            destination,

        "volume_cbm":
            billable_cbm,

        "message":
            "No applicable LCL ocean rate was found."
    }


# =========================================================
# MAIN PRICING FUNCTION
# =========================================================

def get_rate(
    shipment_mode,
    origin,
    destination,
    shipment_type=None,
    container_type=None,
    container_count=1,
    weight_kg=None,
    shipment_date=None,
    cargo_type=None,
    length_cm=None,
    width_cm=None,
    height_cm=None,
    pieces=None,
    volume_cbm=None
):

    shipment_mode = normalize_text(
        shipment_mode
    )

    shipment_date = parse_shipment_date(
        shipment_date
    )

    # =====================================================
    # AIR
    # =====================================================

    if shipment_mode == "air":

        if weight_kg is None:

            return {

                "found": False,

                "status":
                    "missing_information",

                "match_type":
                    "missing_information",

                "mode":
                    "air",

                "message":
                    "Gross weight is required "
                    "for air freight."
            }

        return find_air_rate(

            origin=origin,

            destination=destination,

            weight_kg=weight_kg,

            length_cm=length_cm,

            width_cm=width_cm,

            height_cm=height_cm,

            pieces=pieces,

            volume_cbm=volume_cbm,

            shipment_date=shipment_date,

            cargo_type=cargo_type
        )

    # =====================================================
    # OCEAN
    # =====================================================

    if shipment_mode == "ocean":

        if not shipment_type:

            return {

                "found": False,

                "status":
                    "missing_information",

                "match_type":
                    "missing_information",

                "mode":
                    "ocean",

                "message":
                    "Shipment type is required "
                    "for ocean freight."
            }

        shipment_type = normalize_text(
            shipment_type
        )

        # -------------------------------------------------
        # LCL
        # -------------------------------------------------

        if shipment_type == "lcl":

            if volume_cbm is None:

                return {

                    "found": False,

                    "status":
                        "missing_information",

                    "match_type":
                        "missing_information",

                    "mode":
                        "ocean",

                    "message":
                        "Volume in CBM is required "
                        "for LCL freight."
                }

            return find_ocean_lcl_rate(

                origin=origin,

                destination=destination,

                volume_cbm=volume_cbm,

                shipment_date=shipment_date,

                cargo_type=cargo_type
            )

        # -------------------------------------------------
        # FCL
        # -------------------------------------------------

        if shipment_type == "fcl":

            if not container_type:

                return {

                    "found": False,

                    "status":
                        "missing_information",

                    "match_type":
                        "missing_information",

                    "mode":
                        "ocean",

                    "message":
                        "Container type is required "
                        "for FCL ocean freight."
                }

            exact_rate = find_ocean_exact_rate(

                origin=origin,

                destination=destination,

                shipment_type=shipment_type,

                container_type=container_type,

                container_count=container_count,

                shipment_date=shipment_date,

                cargo_type=cargo_type
            )

            if exact_rate.get("found"):
                return exact_rate

            alternative_rate = (
                find_ocean_alternative_rate(

                    origin=origin,

                    destination=destination,

                    shipment_type=shipment_type,

                    requested_container_type=
                        container_type,

                    container_count=container_count,

                    shipment_date=shipment_date,

                    cargo_type=cargo_type
                )
            )

            if alternative_rate.get("found"):
                return alternative_rate

            if (
                alternative_rate.get(
                    "match_type"
                )
                == "alternative_quantity_exceeded"
            ):

                return {

                    "found": False,

                    "match_type":
                        "alternative_quantity_exceeded",

                    "mode":
                        "ocean",

                    "origin":
                        origin,

                    "destination":
                        destination,

                    "shipment_type":
                        shipment_type,

                    "requested_container_type":
                        normalize_container_type(
                            container_type
                        ),

                    "container_count":
                        container_count,

                    "rejected_alternatives":
                        alternative_rate.get(
                            "rejected_alternatives",
                            []
                        ),

                    "message":
                        alternative_rate.get(
                            "message",
                            "An alternative container rate "
                            "exists, but the requested "
                            "container quantity is outside "
                            "the applicable quantity range."
                        )
                }

            return {

                "found": False,

                "match_type":
                    "none",

                "mode":
                    "ocean",

                "origin":
                    origin,

                "destination":
                    destination,

                "shipment_type":
                    shipment_type,

                "requested_container_type":
                    normalize_container_type(
                        container_type
                    ),

                "container_count":
                    container_count,

                "message":
                    "No applicable exact or alternative "
                    "ocean rate was found for the requested "
                    "shipment quantity and container type."
            }

        # -------------------------------------------------
        # UNKNOWN OCEAN TYPE
        # -------------------------------------------------

        return {

            "found": False,

            "status":
                "missing_information",

            "match_type":
                "missing_information",

            "mode":
                "ocean",

            "message":
                "Shipment type must be FCL or LCL."
        }

    # =====================================================
    # UNKNOWN MODE
    # =====================================================

    return {

        "found": False,

        "match_type":
            "none",

        "status":
            "missing_information",

        "message":
            "Shipment mode must be air or ocean."
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    import json

    print("\n")
    print("=" * 70)
    print("TESTING AIR RATE LOOKUP")
    print("=" * 70)

    result = get_rate(

        shipment_mode="air",

        origin="Mumbai, India",

        destination="Frankfurt, Germany",

        shipment_type="air",

        weight_kg=125,

        length_cm=60,

        width_cm=40,

        height_cm=35,

        pieces=5,

        shipment_date="2026-09-30",

        cargo_type="Engineering Components"
    )

    print("\nAIR RATE RESULT:\n")

    print(
        json.dumps(
            result,
            indent=4,
            default=str
        )
    )