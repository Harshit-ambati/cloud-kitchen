import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";

function MapEvents({ position, onChange }) {
  useMapEvents({
    click(event) {
      onChange({
        lat: event.latlng.lat,
        lng: event.latlng.lng,
      });
    },
  });

  return (
    <Marker
      position={[position.lat, position.lng]}
      draggable
      eventHandlers={{
        dragend: (event) => {
          const marker = event.target;
          const nextPosition = marker.getLatLng();
          onChange({
            lat: nextPosition.lat,
            lng: nextPosition.lng,
          });
        },
      }}
    />
  );
}

export default function LocationPickerMap({ position, onChange }) {
  return (
    <div className="overflow-hidden rounded-[24px] ring-1 ring-slate-200">
      <div className="h-72 w-full">
        <MapContainer center={[position.lat, position.lng]} zoom={13} className="h-full w-full" key={`${position.lat}-${position.lng}`}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <MapEvents position={position} onChange={onChange} />
        </MapContainer>
      </div>
    </div>
  );
}
