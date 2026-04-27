import { useEffect, useMemo, useState } from "react";
import LocationPickerMap from "./LocationPickerMap";
import { DELIVERY_AREAS, FALLBACK_MENU_ITEMS, MENU_IMAGE_MAP } from "../data/menu";

const API_URL = "http://localhost:8000/api";
const KITCHEN_LOCATION = { lat: 17.385, lng: 78.4867 };

const INITIAL_CHECKOUT = {
  customer_name: "",
  customer_phone: "",
  fulfillment_mode: "delivery",
  locality: "",
  street_address: "",
  landmark: "",
  pincode: "",
  user_lat: DELIVERY_AREAS[0].user_lat,
  user_lng: DELIVERY_AREAS[0].user_lng,
  priority: "standard",
  order_type: "regular",
};

const formatPrice = (value) => `Rs. ${value.toFixed(2)}`;

const inferDeliveryAreaByLocality = (locality) => {
  const normalizedLocality = locality.trim().toLowerCase();
  if (!normalizedLocality) {
    return DELIVERY_AREAS[0];
  }

  return (
    DELIVERY_AREAS.find((area) => {
      const searchableText = `${area.label} ${area.address}`.toLowerCase();
      return searchableText.includes(normalizedLocality) || normalizedLocality.includes(area.label.toLowerCase());
    }) || DELIVERY_AREAS[0]
  );
};

const inferDeliveryAreaByCoords = (lat, lng) => {
  if (typeof lat !== "number" || typeof lng !== "number") {
    return DELIVERY_AREAS[0];
  }

  return DELIVERY_AREAS.reduce((closest, candidate) => {
    const currentDistance = (closest.user_lat - lat) ** 2 + (closest.user_lng - lng) ** 2;
    const candidateDistance = (candidate.user_lat - lat) ** 2 + (candidate.user_lng - lng) ** 2;
    return candidateDistance < currentDistance ? candidate : closest;
  }, DELIVERY_AREAS[0]);
};

const buildMenuCategories = (items) => {
  const seen = new Set();

  return items.reduce((categories, item) => {
    if (!seen.has(item.category)) {
      seen.add(item.category);
      categories.push(item.category);
    }

    return categories;
  }, []);
};

export default function OrderForm({ onOrderCreated, onTrackOrder }) {
  const [activeCategory, setActiveCategory] = useState("All");
  const [dietFilter, setDietFilter] = useState("all");
  const [sortBy, setSortBy] = useState("popular");
  const [menuItems, setMenuItems] = useState([]);
  const [menuCategories, setMenuCategories] = useState([]);
  const [menuLoading, setMenuLoading] = useState(true);
  const [cart, setCart] = useState({});
  const [checkout, setCheckout] = useState(INITIAL_CHECKOUT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successOrder, setSuccessOrder] = useState(null);
  const [isPickingLocation, setIsPickingLocation] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [isReverseGeocoding, setIsReverseGeocoding] = useState(false);

  useEffect(() => {
    const fetchMenu = async () => {
      setMenuLoading(true);
      try {
        const res = await fetch(`${API_URL}/menu/`);
        if (!res.ok) {
          throw new Error("Failed to load menu");
        }

        const data = await res.json();
        const fetchedMenuItems = (data.items || []).map((item) => ({
          ...item,
          image: MENU_IMAGE_MAP[item.imageKey || item.id] || MENU_IMAGE_MAP[item.id],
        }));
        const nextMenuItems = fetchedMenuItems.length > 0 ? fetchedMenuItems : FALLBACK_MENU_ITEMS;
        setMenuItems(nextMenuItems);
        setMenuCategories((data.categories || []).length > 0 ? data.categories : buildMenuCategories(nextMenuItems));
      } catch {
        setMenuItems(FALLBACK_MENU_ITEMS);
        setMenuCategories(buildMenuCategories(FALLBACK_MENU_ITEMS));
        setError("Live menu service is unavailable, so showing the built-in menu instead.");
      } finally {
        setMenuLoading(false);
      }
    };

    void fetchMenu();
  }, []);

  useEffect(() => {
    if (activeCategory === "All") {
      return;
    }

    if (!menuCategories.includes(activeCategory)) {
      setActiveCategory("All");
    }
  }, [activeCategory, menuCategories]);

  const selectedArea = useMemo(
    () => {
      if (checkout.locality.trim()) {
        return inferDeliveryAreaByLocality(checkout.locality);
      }

      return inferDeliveryAreaByCoords(checkout.user_lat, checkout.user_lng);
    },
    [checkout.locality, checkout.user_lat, checkout.user_lng],
  );

  const visibleMenu = useMemo(
    () => {
      const filtered = menuItems.filter((item) => {
        const matchesCategory =
          activeCategory === "All"
            ? true
            : item.category === activeCategory || (activeCategory === "Bestsellers" && item.category === "Bestsellers");
        const matchesDiet =
          dietFilter === "all"
            ? true
            : dietFilter === "veg"
              ? item.isVeg
              : !item.isVeg;

        return matchesCategory && matchesDiet;
      });

      const sorted = [...filtered];
      switch (sortBy) {
        case "price-low":
          sorted.sort((left, right) => left.price - right.price);
          break;
        case "price-high":
          sorted.sort((left, right) => right.price - left.price);
          break;
        case "rating":
          sorted.sort((left, right) => right.rating - left.rating);
          break;
        case "eta":
          sorted.sort((left, right) => parseInt(left.eta, 10) - parseInt(right.eta, 10));
          break;
        default:
          sorted.sort((left, right) => right.rating - left.rating);
          break;
      }

      return sorted;
    },
    [activeCategory, dietFilter, menuItems, sortBy],
  );

  const cartItems = useMemo(
    () =>
      Object.entries(cart)
        .map(([itemId, quantity]) => {
          const menuItem = menuItems.find((item) => item.id === itemId);
          if (!menuItem || quantity <= 0) {
            return null;
          }

          return {
            dish_id: menuItem.id,
            name: menuItem.name,
            category: menuItem.category,
            quantity,
            unit_price: menuItem.price,
            line_total: quantity * menuItem.price,
          };
        })
        .filter(Boolean),
    [cart, menuItems],
  );

  const itemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = cartItems.reduce((sum, item) => sum + item.line_total, 0);
  const isTakeaway = checkout.fulfillment_mode === "takeaway";
  const deliveryFee = itemCount > 0 && !isTakeaway ? selectedArea.deliveryFee : 0;
  const platformFee = itemCount > 0 ? 9 : 0;
  const taxes = Number((subtotal * 0.05).toFixed(2));
  const totalAmount = subtotal + deliveryFee + platformFee + taxes;
  const pickupReadyMinutes = 18 + (checkout.order_type === "express" ? -6 : 0) + Math.min(cartItems.length * 2, 10);

  const updateQuantity = (itemId, nextQuantity) => {
    if (successOrder) {
      setSuccessOrder(null);
    }

    setCart((current) => {
      if (nextQuantity <= 0) {
        const updated = { ...current };
        delete updated[itemId];
        return updated;
      }

      return {
        ...current,
        [itemId]: nextQuantity,
      };
    });
  };

  const handleCheckoutChange = ({ target: { name, value } }) => {
    if (successOrder) {
      setSuccessOrder(null);
    }

    setCheckout((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const reverseGeocodeLocation = async ({ lat, lng }) => {
    setIsReverseGeocoding(true);
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&addressdetails=1&zoom=18`,
        {
          headers: {
            "Accept-Language": "en",
          },
        },
      );

      if (!response.ok) {
        throw new Error("Reverse geocoding request failed");
      }

      const data = await response.json();
      const address = data.address || {};
      const locality =
        address.suburb ||
        address.neighbourhood ||
        address.city_district ||
        address.city ||
        address.town ||
        address.village ||
        inferDeliveryAreaByCoords(lat, lng).label;
      const streetAddress = [address.house_number, address.road].filter(Boolean).join(", ");
      const landmark =
        address.building ||
        address.amenity ||
        address.shop ||
        address.office ||
        "";

      setCheckout((current) => ({
        ...current,
        locality,
        street_address: streetAddress || current.street_address,
        landmark: landmark || current.landmark,
        pincode: address.postcode || current.pincode,
      }));
    } catch {
      setError("We found the location pin, but couldn't auto-fill the address. You can still type it manually.");
    } finally {
      setIsReverseGeocoding(false);
    }
  };

  const handleLocationChange = ({ lat, lng }) => {
    const nearestArea = inferDeliveryAreaByCoords(lat, lng);
    setCheckout((current) => ({
      ...current,
      user_lat: lat,
      user_lng: lng,
      locality: current.locality.trim() ? current.locality : nearestArea.label,
    }));
    setError("");
    void reverseGeocodeLocation({ lat, lng });
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError("Your browser does not support location access. Please pick your spot on the map.");
      return;
    }

    setIsLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        handleLocationChange({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setIsLocating(false);
        setIsPickingLocation(true);
      },
      () => {
        setIsLocating(false);
        setError("Could not fetch your current location. You can still drop a pin manually on the map.");
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!cartItems.length) {
      setError("Add at least one dish to place an order.");
      return;
    }
    if (!isTakeaway && (!checkout.locality.trim() || !checkout.street_address.trim())) {
      setError("Enter your delivery locality and full street address to place the order.");
      return;
    }

    setLoading(true);
    setError("");

    const deliveryAddress = isTakeaway
      ? "Collect from Cloud Kitchen Express, Hyderabad"
      : [
          checkout.street_address.trim(),
          checkout.landmark.trim() ? `Landmark: ${checkout.landmark.trim()}` : "",
          checkout.locality.trim(),
          checkout.pincode.trim(),
        ]
          .filter(Boolean)
          .join(", ");

    const payload = {
      user_lat: isTakeaway ? KITCHEN_LOCATION.lat : checkout.user_lat,
      user_lng: isTakeaway ? KITCHEN_LOCATION.lng : checkout.user_lng,
      kitchen_lat: KITCHEN_LOCATION.lat,
      kitchen_lng: KITCHEN_LOCATION.lng,
      fulfillment_mode: checkout.fulfillment_mode,
      order_type: checkout.order_type,
      priority: checkout.priority,
      customer_name: checkout.customer_name || "Guest",
      customer_phone: checkout.customer_phone,
      delivery_area: isTakeaway ? "Restaurant pickup" : checkout.locality.trim(),
      delivery_address: deliveryAddress,
      restaurant_name: "Cloud Kitchen Express",
      items: cartItems,
      item_count: itemCount,
      subtotal,
      delivery_fee: deliveryFee,
      platform_fee: platformFee,
      taxes,
      total_amount: totalAmount,
    };

    try {
      const res = await fetch(`${API_URL}/orders/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to create order");
      }

      const data = await res.json();
      onOrderCreated(data);
      setCart({});
      setCheckout(INITIAL_CHECKOUT);
      setSuccessOrder(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      {successOrder ? (
        <div className="overflow-hidden rounded-[30px] bg-[linear-gradient(135deg,#fff7ed_0%,#ffffff_45%,#ecfeff_100%)] p-6 shadow-[0_18px_50px_rgba(15,23,42,0.08)] ring-1 ring-orange-100">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-orange-600">Order confirmed</p>
              <h3 className="mt-2 text-3xl font-black text-slate-950">
                Order #{successOrder.id.slice(-6)} was placed successfully.
              </h3>
              <p className="mt-3 text-sm text-slate-600">
                {successOrder.fulfillment_mode === "takeaway"
                  ? `Pickup is expected around ${new Date(successOrder.pickup_ready_at).toLocaleString()}. We will move it to ready for pickup once the kitchen finishes.`
                  : `Your order is now in the live queue for ${successOrder.delivery_area || "your location"}, with an ETA of about ${successOrder.predicted_eta_minutes} minutes.`}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(successOrder.items || []).map((item) => (
                  <span
                    key={`success-${successOrder.id}-${item.dish_id}`}
                    className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200"
                  >
                    {item.name} x{item.quantity}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] bg-slate-950 px-5 py-5 text-white lg:min-w-72">
              <p className="text-xs uppercase tracking-[0.2em] text-orange-200">Bill summary</p>
              <p className="mt-2 text-3xl font-black">{formatPrice(successOrder.total_amount || 0)}</p>
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-300">
                <p>
                  Items
                  <span className="mt-1 block font-semibold text-white">{successOrder.item_count || 0}</span>
                </p>
                <p>
                  Mode
                  <span className="mt-1 block font-semibold capitalize text-white">{successOrder.fulfillment_mode}</span>
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onTrackOrder(successOrder.id)}
              className="rounded-full bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600"
            >
              Track order
            </button>
            <button
              type="button"
              onClick={() => setSuccessOrder(null)}
              className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-orange-300 hover:text-orange-600"
            >
              Continue browsing
            </button>
          </div>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-[32px] bg-white shadow-[0_24px_80px_rgba(15,23,42,0.08)] ring-1 ring-orange-100">
        <div className="bg-[radial-gradient(circle_at_top_left,_rgba(251,146,60,0.25),_transparent_32%),linear-gradient(135deg,#fff7ed_0%,#ffffff_45%,#fef2f2_100%)] px-6 py-8 md:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <span className="inline-flex rounded-full bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-orange-600 ring-1 ring-orange-200">
                Swiggy / Zomato style ordering
              </span>
              <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900 md:text-5xl">
                Discover dishes, compare prices, and place orders in one flow.
              </h2>
              <p className="mt-3 max-w-xl text-sm text-slate-600 md:text-base">
                This version keeps your ETA and rider assignment engine, but the top experience now behaves like a proper food delivery app.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
              <div className="rounded-2xl bg-white/80 p-4 ring-1 ring-orange-100 backdrop-blur">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Live Menu</p>
                <p className="mt-2 text-2xl font-bold text-slate-900">{menuItems.length}</p>
                <p>Dishes available now</p>
              </div>
              <div className="rounded-2xl bg-slate-900 p-4 text-white shadow-lg">
                <p className="text-xs uppercase tracking-[0.2em] text-orange-200">{isTakeaway ? "Pickup Promise" : "Fast Delivery"}</p>
                <p className="mt-2 text-2xl font-bold">{isTakeaway ? `${pickupReadyMinutes} min` : `${selectedArea.deliveryFee} Rs`}</p>
                <p className="text-slate-300">{isTakeaway ? "Estimated collection time" : `Fee for ${selectedArea.label}`}</p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            {["All", ...menuCategories].map((category) => (
              <button
                key={category}
                type="button"
                onClick={() => setActiveCategory(category)}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  activeCategory === category
                    ? "bg-slate-900 text-white shadow-lg"
                    : "bg-white/80 text-slate-700 ring-1 ring-slate-200 hover:bg-white"
                }`}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="mt-6 grid gap-3 lg:grid-cols-2">
            <label className="rounded-2xl bg-white/85 px-4 py-3 ring-1 ring-slate-200">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Food type</span>
              <select
                value={dietFilter}
                onChange={(event) => setDietFilter(event.target.value)}
                className="w-full bg-transparent text-sm text-slate-800 outline-none"
              >
                <option value="all">All</option>
                <option value="veg">Veg only</option>
                <option value="non-veg">Non-veg only</option>
              </select>
            </label>

            <label className="rounded-2xl bg-white/85 px-4 py-3 ring-1 ring-slate-200">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sort by</span>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
                className="w-full bg-transparent text-sm text-slate-800 outline-none"
              >
                <option value="popular">Popular</option>
                <option value="rating">Rating</option>
                <option value="price-low">Price: Low to High</option>
                <option value="price-high">Price: High to Low</option>
                <option value="eta">Faster delivery</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.55fr_0.95fr]">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-2xl font-black text-slate-900">{activeCategory}</h3>
              <p className="text-sm text-slate-500">
                {menuLoading ? "Loading menu..." : `${visibleMenu.length} matching dishes with visible pricing and quick add controls.`}
              </p>
            </div>
            <div className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-600 ring-1 ring-slate-200">
              {itemCount} item{itemCount === 1 ? "" : "s"} in cart
            </div>
          </div>

          {menuLoading ? (
            <div className="rounded-[28px] border border-dashed border-slate-200 bg-white px-6 py-12 text-center shadow-[0_18px_50px_rgba(15,23,42,0.04)]">
              <p className="text-lg font-semibold text-slate-800">Loading the live menu</p>
              <p className="mt-2 text-sm text-slate-500">Fetching dishes and pricing from the restaurant catalog.</p>
            </div>
          ) : visibleMenu.length === 0 ? (
            <div className="rounded-[28px] border border-dashed border-slate-200 bg-white px-6 py-12 text-center shadow-[0_18px_50px_rgba(15,23,42,0.04)]">
              <p className="text-lg font-semibold text-slate-800">No dishes matched these filters</p>
              <p className="mt-2 text-sm text-slate-500">Try a different cuisine or switch the veg filter.</p>
            </div>
          ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {visibleMenu.map((item) => {
              const quantity = cart[item.id] || 0;

              return (
                <article
                  key={item.id}
                  className="overflow-hidden rounded-[28px] bg-white shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200"
                >
                  <div className="relative h-48 overflow-hidden">
                    <img
                      src={item.image}
                      alt={item.name}
                      className="h-full w-full object-cover transition duration-500 hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950/65 via-slate-900/10 to-transparent" />
                    <div className="absolute inset-x-0 top-0 flex items-start justify-between p-5">
                      <span className="rounded-full bg-white/85 px-3 py-1 text-xs font-bold uppercase tracking-[0.22em] text-slate-700">
                        {item.isVeg ? "Veg" : "Non-Veg"}
                      </span>
                      <span className="rounded-full bg-slate-900/80 px-3 py-1 text-xs font-semibold text-white">
                        {item.rating} star
                      </span>
                    </div>
                    <div className="absolute inset-x-0 bottom-0 p-5 text-white">
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-200">{item.category}</p>
                      <div className="mt-2 flex items-end justify-between gap-4">
                        <div>
                          <h4 className="text-2xl font-black leading-tight">{item.name}</h4>
                          <p className="mt-1 text-sm text-white/85">{item.eta}</p>
                        </div>
                        <p className="text-xl font-black">Rs. {item.price}</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4 p-5">
                    <div>
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Popular pick</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-slate-500">Category: {item.category}</p>

                      {quantity === 0 ? (
                        <button
                          type="button"
                          onClick={() => updateQuantity(item.id, 1)}
                          className="rounded-full bg-orange-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-orange-600"
                        >
                          Add
                        </button>
                      ) : (
                        <div className="inline-flex items-center gap-3 rounded-full bg-slate-900 px-3 py-2 text-white">
                          <button
                            type="button"
                            onClick={() => updateQuantity(item.id, quantity - 1)}
                            className="h-7 w-7 rounded-full bg-white/15 text-lg leading-none"
                          >
                            -
                          </button>
                          <span className="min-w-5 text-center text-sm font-bold">{quantity}</span>
                          <button
                            type="button"
                            onClick={() => updateQuantity(item.id, quantity + 1)}
                            className="h-7 w-7 rounded-full bg-white/15 text-lg leading-none"
                          >
                            +
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="rounded-[30px] bg-slate-950 p-6 text-white shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-orange-200">Checkout</p>
                <h3 className="mt-2 text-3xl font-black">Your cart</h3>
              </div>
              <div className="rounded-2xl bg-white/10 px-4 py-3 text-right">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-300">Grand Total</p>
                <p className="mt-1 text-2xl font-black">{formatPrice(totalAmount)}</p>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              {cartItems.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/20 px-4 py-8 text-center text-sm text-slate-300">
                  Add dishes from the menu to build a real itemized order.
                </div>
              ) : (
                cartItems.map((item) => (
                  <div key={item.dish_id} className="flex items-center justify-between rounded-2xl bg-white/8 px-4 py-3">
                    <div className="min-w-0">
                      <p className="font-semibold">{item.name}</p>
                      <p className="text-sm text-slate-300">
                        {item.quantity} x Rs. {item.unit_price}
                      </p>
                    </div>
                    <div className="ml-4 flex items-center gap-3">
                      <p className="font-bold">{formatPrice(item.line_total)}</p>
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.dish_id, 0)}
                        aria-label={`Remove ${item.name} from cart`}
                        title="Remove from cart"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/20 text-rose-200 transition hover:border-rose-300 hover:text-white"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 fill-none stroke-current stroke-2">
                          <path d="M4 7h16" />
                          <path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                          <path d="M7 7l1 12a1 1 0 0 0 1 .9h6a1 1 0 0 0 1-.9L17 7" />
                          <path d="M10 11v5" />
                          <path d="M14 11v5" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

      <div className="mt-6 space-y-3 rounded-[24px] bg-white px-5 py-4 text-sm text-slate-700">
              <div className="flex items-center justify-between">
                <span>Item total</span>
                <span className="font-semibold">{formatPrice(subtotal)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Delivery fee</span>
                <span className="font-semibold">{formatPrice(deliveryFee)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Platform fee</span>
                <span className="font-semibold">{formatPrice(platformFee)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>GST & restaurant charges (5%)</span>
                <span className="font-semibold">{formatPrice(taxes)}</span>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200 pt-3 text-base font-bold text-slate-950">
                <span>To pay</span>
                <span>{formatPrice(totalAmount)}</span>
              </div>
              {isTakeaway ? (
                <p className="text-xs text-slate-500">
                  Pickup ready in about {pickupReadyMinutes} minutes after the kitchen starts preparing your order.
                </p>
              ) : (
                <p className="text-xs text-slate-500">
                  Delivery ETA is based on the map pin and nearest service zone around {selectedArea.label}.
                </p>
              )}
            </div>
          </div>

          <div className="rounded-[30px] bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200">
            <h3 className="text-xl font-black text-slate-900">Order details</h3>
            <div className="mt-5 grid gap-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Fulfillment mode</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: "delivery", label: "Delivery", note: "Doorstep order with rider ETA" },
                    { id: "takeaway", label: "Takeaway", note: "Pick up from the restaurant" },
                  ].map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() =>
                        setCheckout((current) => ({
                          ...current,
                          fulfillment_mode: option.id,
                        }))
                      }
                      className={`rounded-2xl border px-4 py-4 text-left transition ${
                        checkout.fulfillment_mode === option.id
                          ? "border-orange-400 bg-orange-50 ring-2 ring-orange-100"
                          : "border-slate-200 bg-white hover:border-orange-200"
                      }`}
                    >
                      <p className="text-sm font-bold text-slate-900">{option.label}</p>
                      <p className="mt-1 text-xs text-slate-500">{option.note}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Customer name</label>
                <input
                  type="text"
                  name="customer_name"
                  value={checkout.customer_name}
                  onChange={handleCheckoutChange}
                  placeholder="Enter customer name"
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Phone number</label>
                <input
                  type="text"
                  name="customer_phone"
                  value={checkout.customer_phone}
                  onChange={handleCheckoutChange}
                  placeholder="98xxxxxx12"
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                />
              </div>

              {isTakeaway ? (
                <div className="rounded-2xl bg-orange-50 px-4 py-4 ring-1 ring-orange-100">
                  <p className="text-sm font-semibold text-slate-900">Pickup from Cloud Kitchen Express</p>
                  <p className="mt-1 text-sm text-slate-600">Hyderabad kitchen</p>
                  <p className="mt-2 text-xs text-slate-500">
                    Your order will be prepared first, then shown as ready for pickup with a collection time.
                  </p>
                </div>
              ) : (
                <>
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-slate-700">Locality / area</label>
                    <input
                      type="text"
                      name="locality"
                      value={checkout.locality}
                      onChange={handleCheckoutChange}
                      placeholder="Banjara Hills, Jubilee Hills, Gachibowli..."
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                    />
                    <p className="mt-2 text-xs text-slate-500">
                      Delivery fee and ETA are estimated using the nearest service zone. Current match: {selectedArea.label}
                    </p>
                  </div>

                  <div className="rounded-2xl bg-slate-50 px-4 py-4 ring-1 ring-slate-200">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">Delivery pin</p>
                        <p className="mt-1 text-xs text-slate-500">
                          Lat {checkout.user_lat.toFixed(4)}, Lng {checkout.user_lng.toFixed(4)}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {isReverseGeocoding ? "Auto-filling address from selected pin..." : "Address fields can auto-fill from your pin."}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={useCurrentLocation}
                          disabled={isLocating}
                          className="rounded-full bg-slate-900 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-white transition hover:bg-slate-800 disabled:opacity-60"
                        >
                          {isLocating ? "Locating..." : "Use Current Location"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setIsPickingLocation((current) => !current)}
                          className="rounded-full border border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-700 transition hover:border-orange-300 hover:text-orange-600"
                        >
                          {isPickingLocation ? "Hide Map" : "Pick on Map"}
                        </button>
                      </div>
                    </div>

                    {isPickingLocation ? (
                      <div className="mt-4 space-y-3">
                        <LocationPickerMap
                          position={{ lat: checkout.user_lat, lng: checkout.user_lng }}
                          onChange={handleLocationChange}
                        />
                        <p className="text-xs text-slate-500">
                          Click anywhere on the map or drag the marker to set the exact delivery spot.
                        </p>
                      </div>
                    ) : null}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-semibold text-slate-700">Flat / house / street address</label>
                    <textarea
                      name="street_address"
                      value={checkout.street_address}
                      onChange={handleCheckoutChange}
                      placeholder="Flat no, building, street name"
                      rows={3}
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-sm font-semibold text-slate-700">Landmark</label>
                      <input
                        type="text"
                        name="landmark"
                        value={checkout.landmark}
                        onChange={handleCheckoutChange}
                        placeholder="Nearby store, apartment gate, metro..."
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                      />
                    </div>
                    <div>
                      <label className="mb-2 block text-sm font-semibold text-slate-700">Pincode</label>
                      <input
                        type="text"
                        name="pincode"
                        value={checkout.pincode}
                        onChange={handleCheckoutChange}
                        placeholder="500081"
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                      />
                    </div>
                  </div>
                </>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Delivery speed</label>
                  <select
                    name="order_type"
                    value={checkout.order_type}
                    onChange={handleCheckoutChange}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                  >
                    <option value="regular">Regular</option>
                    <option value="express">Express</option>
                    <option value="veg">Veg Priority</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Kitchen priority</label>
                  <select
                    name="priority"
                    value={checkout.priority}
                    onChange={handleCheckoutChange}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                  >
                    <option value="standard">Standard</option>
                    <option value="high">High</option>
                    <option value="urgent">Rush</option>
                  </select>
                </div>
              </div>
            </div>

            {error ? <p className="mt-4 text-sm font-medium text-rose-500">{error}</p> : null}

            <button
              type="submit"
              disabled={loading}
              className="mt-6 w-full rounded-2xl bg-orange-500 px-5 py-4 text-sm font-bold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Placing order..." : `Place order for ${formatPrice(totalAmount)}`}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
