import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import LocationPickerMap from "./LocationPickerMap";
import { DELIVERY_AREAS, FALLBACK_MENU_ITEMS, MENU_IMAGE_MAP } from "../data/menu";
import { ShoppingCart, Plus, Minus, Trash2, Coffee, IceCream, UtensilsCrossed, Pizza, Soup, ChefHat, Utensils } from "lucide-react";

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

const pageVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.08 },
  },
};

const sectionVariants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.42, ease: "easeOut" } },
};

const spring = { type: "spring", stiffness: 280, damping: 24 };
void motion;
const formatPrice = (value) => `Rs. ${(value || 0).toFixed(2)}`;

const inferDeliveryAreaByLocality = (locality) => {
  const normalizedLocality = locality.trim().toLowerCase();
  if (!normalizedLocality) return DELIVERY_AREAS[0];

  return (
    DELIVERY_AREAS.find((area) => {
      const searchableText = `${area.label} ${area.address}`.toLowerCase();
      return searchableText.includes(normalizedLocality) || normalizedLocality.includes(area.label.toLowerCase());
    }) || DELIVERY_AREAS[0]
  );
};

const inferDeliveryAreaByCoords = (lat, lng) => {
  if (typeof lat !== "number" || typeof lng !== "number") return DELIVERY_AREAS[0];

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

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</span>
      {children}
    </label>
  );
}

function MotionButton({ className = "", children, ...props }) {
  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.95 }}
      transition={spring}
      className={className}
      {...props}
    >
      {children}
    </motion.button>
  );
}

function Icon({ name, className = "h-4 w-4" }) {
  if (name === "cart") return <ShoppingCart className={className} />;
  if (name === "cart-plus") return <Plus className={className} />;
  if (name === "minus") return <Minus className={className} />;
  if (name === "plus") return <Plus className={className} />;
  if (name === "trash") return <Trash2 className={className} />;
  return null;
}

function Navbar({ itemCount, searchTerm, setSearchTerm, onCartClick }) {
  return (
    <motion.nav
      variants={sectionVariants}
      className="flex flex-col gap-4 rounded-3xl border border-white/70 bg-white/85 p-4 shadow-md backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between"
    >
      <div className="flex items-center gap-3">
        <img src="/logo.png" alt="Cloud Kitchen logo" className="h-12 w-12 rounded-2xl object-cover shadow-md" />
        <div>
          <p className="font-semibold text-gray-900">Cloud Kitchen</p>
          <p className="text-sm text-gray-500">Premium meals, live dispatch</p>
        </div>
      </div>

      <div className="min-w-0 flex-1 lg:max-w-xl">
        <input
          type="search"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Search biryani, rolls, ramen..."
          className="w-full rounded-full border border-gray-200 bg-gray-100 px-5 py-3 text-sm text-gray-800 outline-none transition focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-300"
        />
      </div>

      <div className="flex items-center justify-between gap-3 lg:justify-end">
        <MotionButton
          type="button"
          onClick={onCartClick}
          aria-label={`Open cart with ${itemCount} item${itemCount === 1 ? "" : "s"}`}
          className="relative inline-flex items-center gap-2 rounded-full bg-gray-100 px-4 py-3 text-sm font-semibold text-gray-700"
        >
          <Icon name="cart" />
          <span>Cart</span>
          <AnimatePresence>
            {itemCount > 0 ? (
              <motion.span
                key={itemCount}
                initial={{ scale: 0, y: 4 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0, y: 4 }}
                className="absolute -right-2 -top-2 rounded-full bg-orange-500 px-2 py-1 text-xs font-bold leading-none text-white"
              >
                {itemCount}
              </motion.span>
            ) : null}
          </AnimatePresence>
        </MotionButton>
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-orange-500 to-red-500 text-sm font-bold text-white shadow-md">
          CK
        </div>
      </div>
    </motion.nav>
  );
}

function HeroSection({ featuredImage, selectedArea, isTakeaway, pickupReadyMinutes }) {
  return (
    <motion.section
      variants={sectionVariants}
      initial={{ opacity: 0, scale: 0.98, y: 22 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="overflow-hidden rounded-3xl bg-gradient-to-br from-orange-500 via-orange-400 to-red-500 p-6 text-white shadow-xl md:p-10"
    >
      <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
        <div>
          <p className="mb-4 inline-flex rounded-full bg-white/20 px-4 py-2 text-sm font-semibold backdrop-blur">
            {isTakeaway ? `Pickup in ${pickupReadyMinutes} min` : `Serving ${selectedArea.label}`}
          </p>
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight text-white md:text-6xl">
            Craving something delicious?
          </h1>
          <p className="mt-4 max-w-xl text-base text-white/85 md:text-lg">
            Order chef-crafted meals with fast delivery, live ETA, and a smart kitchen workflow built for freshness.
          </p>
          <MotionButton
            type="button"
            onClick={() => document.getElementById("menu-grid")?.scrollIntoView({ behavior: "smooth" })}
            className="mt-7 rounded-full bg-white px-6 py-3 text-sm font-bold text-orange-600 shadow-lg transition hover:shadow-xl"
          >
            Order Now
          </MotionButton>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ ...spring, delay: 0.12 }}
          className="relative min-h-64"
        >
          <div className="absolute inset-0 rounded-full bg-white/20 blur-3xl" />
          <img
            src={featuredImage}
            alt="Featured food"
            className="relative ml-auto aspect-square max-h-80 rounded-full object-cover shadow-2xl ring-8 ring-white/20"
          />
        </motion.div>
      </div>
    </motion.section>
  );
}

function CategoryTabs({ categories, activeCategory, setActiveCategory }) {
  const getCategoryIcon = (category) => {
    switch (category.toLowerCase()) {
      case "all": return <Utensils className="h-4 w-4 shrink-0" />;
      case "bestsellers": return <ChefHat className="h-4 w-4 shrink-0" />;
      case "biryani": return <UtensilsCrossed className="h-4 w-4 shrink-0" />;
      case "rolls": return <Pizza className="h-4 w-4 shrink-0" />;
      case "bowls": return <Soup className="h-4 w-4 shrink-0" />;
      case "italian": return <Pizza className="h-4 w-4 shrink-0" />;
      case "chinese": return <Utensils className="h-4 w-4 shrink-0" />;
      case "korean": return <Utensils className="h-4 w-4 shrink-0" />;
      case "ramen": return <Soup className="h-4 w-4 shrink-0" />;
      case "beverages": return <Coffee className="h-4 w-4 shrink-0" />;
      case "desserts": return <IceCream className="h-4 w-4 shrink-0" />;
      case "north indian": return <UtensilsCrossed className="h-4 w-4 shrink-0" />;
      case "breads": return <Utensils className="h-4 w-4 shrink-0" />;
      default: return <Utensils className="h-4 w-4 shrink-0" />;
    }
  };

  return (
    <motion.div variants={sectionVariants} className="flex gap-3 overflow-x-auto pb-2">
      {["All", ...categories].map((category) => (
        <MotionButton
          key={category}
          type="button"
          onClick={() => setActiveCategory(category)}
          className={`shrink-0 flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold shadow-sm transition ${
            activeCategory === category
              ? "bg-orange-500 text-white shadow-lg shadow-orange-500/25"
              : "bg-white text-gray-700 hover:bg-orange-50 hover:text-orange-600"
          }`}
        >
          {getCategoryIcon(category)}
          {category}
        </MotionButton>
      ))}
    </motion.div>
  );
}

function FoodCard({ item, quantity, updateQuantity }) {
  return (
    <motion.article
      layout
      variants={sectionVariants}
      whileHover={{ y: -6, scale: 1.015 }}
      transition={spring}
      className="group flex h-full flex-col overflow-hidden rounded-2xl bg-white shadow-md transition-shadow hover:shadow-xl"
    >
      <div className="relative h-52 shrink-0 overflow-hidden">
        <img src={item.image} alt={item.name} className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-950/75 via-gray-900/10 to-transparent" />
        <span className="absolute left-4 top-4 rounded-full bg-white/75 px-3 py-1 text-xs font-semibold text-yellow-700 shadow-sm backdrop-blur-xl">
          {item.rating} star
        </span>
        <MotionButton
          type="button"
          aria-label={`Add ${item.name} to cart`}
          onClick={() => updateQuantity(item.id, quantity + 1)}
          className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-orange-500 to-red-500 text-2xl font-semibold leading-none text-white shadow-lg"
        >
          <Icon name="cart-plus" className="h-5 w-5" />
        </MotionButton>
        <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3">
          <div>
            <span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.isVeg ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
              {item.isVeg ? "Veg" : "Non-Veg"}
            </span>
            <h3 className="mt-3 text-lg font-semibold text-white">{item.name}</h3>
          </div>
          <p className="rounded-full bg-white/85 px-3 py-1 text-sm font-bold text-orange-600 backdrop-blur">
            Rs. {item.price}
          </p>
        </div>
      </div>

      <div className="flex flex-1 flex-col p-4">
        <p className="h-[4.5rem] overflow-hidden text-sm leading-6 text-gray-500">{item.description}</p>
        <div className="mt-auto flex min-h-11 items-center justify-between gap-3 pt-4">
          <p className="text-sm font-medium text-gray-500">{item.eta}</p>
          {quantity === 0 ? (
            <MotionButton
              type="button"
              onClick={() => updateQuantity(item.id, 1)}
              className="inline-flex items-center gap-2 rounded-full bg-orange-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-orange-600"
            >
              <Icon name="cart-plus" />
              <span>Add</span>
            </MotionButton>
          ) : (
            <motion.div layout className="flex items-center gap-3 rounded-full bg-gray-800 px-3 py-2 text-white shadow-md">
              <MotionButton
                type="button"
                aria-label={`Remove one ${item.name} from cart`}
                onClick={() => updateQuantity(item.id, quantity - 1)}
                className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15"
              >
                <Icon name="minus" className="h-3.5 w-3.5" />
              </MotionButton>
              <span className="min-w-5 text-center text-sm font-bold">{quantity}</span>
              <MotionButton
                type="button"
                aria-label={`Add one more ${item.name} to cart`}
                onClick={() => updateQuantity(item.id, quantity + 1)}
                className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15"
              >
                <Icon name="plus" className="h-3.5 w-3.5" />
              </MotionButton>
            </motion.div>
          )}
        </div>
      </div>
    </motion.article>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <motion.div
          key={`skeleton-${index}`}
          variants={sectionVariants}
          className="overflow-hidden rounded-2xl bg-white shadow-md"
        >
          <div className="h-52 animate-pulse bg-gray-200" />
          <div className="space-y-4 p-4">
            <div className="h-4 w-2/3 animate-pulse rounded-full bg-gray-200" />
            <div className="h-3 w-full animate-pulse rounded-full bg-gray-200" />
            <div className="h-3 w-4/5 animate-pulse rounded-full bg-gray-200" />
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function CartPanel({
  cartItems,
  itemCount,
  subtotal,
  deliveryFee,
  platformFee,
  taxes,
  totalAmount,
  checkout,
  setCheckout,
  handleCheckoutChange,
  updateQuantity,
  isTakeaway,
  pickupReadyMinutes,
  isReverseGeocoding,
  isLocating,
  useCurrentLocation,
  isPickingLocation,
  setIsPickingLocation,
  handleLocationChange,
  loading,
  error,
  handleSubmit,
}) {
  return (
    <motion.aside
      id="cart-panel"
      tabIndex={-1}
      initial={{ opacity: 0, x: 48 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ ...spring, delay: 0.18 }}
      className="lg:sticky lg:top-6 lg:self-start"
    >
      <form
        onSubmit={handleSubmit}
        className="overflow-hidden rounded-t-3xl border border-white/70 bg-white/75 shadow-xl backdrop-blur-xl lg:rounded-3xl"
      >
        <div className="bg-gradient-to-br from-gray-900 to-gray-800 p-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-orange-300">Order summary</p>
              <h2 className="mt-1 text-lg font-semibold text-white">Your cart</h2>
            </div>
            <motion.div
              key={itemCount}
              initial={{ scale: 0.94 }}
              animate={{ scale: 1 }}
              transition={spring}
              className="rounded-2xl bg-white/10 px-4 py-3 text-right"
            >
              <p className="text-xs text-gray-300">Total</p>
              <p className="text-xl font-bold text-orange-400">{formatPrice(totalAmount)}</p>
            </motion.div>
          </div>

          <div className="mt-6 space-y-3">
            <AnimatePresence initial={false}>
              {cartItems.length === 0 ? (
                <motion.div
                  key="empty-cart"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="rounded-2xl border border-dashed border-white/20 px-4 py-8 text-center"
                >
                  <p className="font-semibold text-white">Your cart is empty</p>
                  <p className="mt-2 text-sm text-gray-300">Add a dish to start building your order.</p>
                </motion.div>
              ) : (
                cartItems.map((item) => (
                  <motion.div
                    key={item.dish_id}
                    layout
                    initial={{ opacity: 0, x: 20, scale: 0.98 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, x: 20, scale: 0.96 }}
                    transition={spring}
                    className="flex items-center justify-between rounded-2xl bg-white/10 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">{item.name}</p>
                      <p className="text-xs text-gray-300">
                        {item.quantity} x Rs. {item.unit_price}
                      </p>
                    </div>
                    <div className="ml-3 flex items-center gap-3">
                      <p className="text-sm font-bold text-white">{formatPrice(item.line_total)}</p>
                      <MotionButton
                        type="button"
                        onClick={() => updateQuantity(item.dish_id, 0)}
                        aria-label={`Remove ${item.name} from cart`}
                        className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-orange-300 transition hover:bg-red-500/20 hover:text-red-400"
                      >
                        <Icon name="trash" className="h-4 w-4" />
                      </MotionButton>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="max-h-[62vh] space-y-5 overflow-y-auto p-6 lg:max-h-none">
          <div className="space-y-3 rounded-2xl bg-gray-50 p-4 text-sm text-gray-700">
            <div className="flex justify-between">
              <span>Item total</span>
              <span className="font-semibold">{formatPrice(subtotal)}</span>
            </div>
            <div className="flex justify-between">
              <span>Delivery fee</span>
              <span className="font-semibold">{formatPrice(deliveryFee)}</span>
            </div>
            <div className="flex justify-between">
              <span>Platform fee</span>
              <span className="font-semibold">{formatPrice(platformFee)}</span>
            </div>
            <div className="flex justify-between">
              <span>GST</span>
              <span className="font-semibold">{formatPrice(taxes)}</span>
            </div>
            <div className="flex justify-between border-t border-gray-200 pt-3 text-base font-bold text-gray-900">
              <span>To pay</span>
              <span className="text-orange-500">{formatPrice(totalAmount)}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { id: "delivery", label: "Delivery" },
              { id: "takeaway", label: "Takeaway" },
            ].map((option) => (
              <MotionButton
                key={option.id}
                type="button"
                onClick={() => setCheckout((current) => ({ ...current, fulfillment_mode: option.id }))}
                className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${
                  checkout.fulfillment_mode === option.id
                    ? "border-orange-500 bg-orange-500 text-white"
                    : "border-gray-200 bg-white text-gray-700 hover:border-orange-300"
                }`}
              >
                {option.label}
              </MotionButton>
            ))}
          </div>

          <div className="grid gap-3">
            <Field label="Customer name">
              <input
                type="text"
                name="customer_name"
                value={checkout.customer_name}
                onChange={handleCheckoutChange}
                placeholder="Enter customer name"
                className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
              />
            </Field>
            <Field label="Phone number">
              <input
                type="text"
                name="customer_phone"
                value={checkout.customer_phone}
                onChange={handleCheckoutChange}
                placeholder="98xxxxxx12"
                className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
              />
            </Field>

            {!isTakeaway ? (
              <>
                <Field label="Locality / area">
                  <input
                    type="text"
                    name="locality"
                    value={checkout.locality}
                    onChange={handleCheckoutChange}
                    placeholder="Banjara Hills, Jubilee Hills..."
                    className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                  />
                </Field>
                <div className="rounded-2xl bg-gray-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Delivery pin</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {isReverseGeocoding ? "Auto-filling address..." : `Lat ${checkout.user_lat.toFixed(4)}, Lng ${checkout.user_lng.toFixed(4)}`}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <MotionButton type="button" onClick={useCurrentLocation} disabled={isLocating} className="rounded-full bg-gray-900 px-3 py-2 text-xs font-bold text-white">
                        {isLocating ? "Locating" : "Use GPS"}
                      </MotionButton>
                      <MotionButton type="button" onClick={() => setIsPickingLocation((current) => !current)} className="rounded-full border border-gray-300 px-3 py-2 text-xs font-bold text-gray-700">
                        {isPickingLocation ? "Hide" : "Map"}
                      </MotionButton>
                    </div>
                  </div>
                  <AnimatePresence>
                    {isPickingLocation ? (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-4 overflow-hidden"
                      >
                        <LocationPickerMap position={{ lat: checkout.user_lat, lng: checkout.user_lng }} onChange={handleLocationChange} />
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>
                <Field label="Full address">
                  <textarea
                    name="street_address"
                    value={checkout.street_address}
                    onChange={handleCheckoutChange}
                    placeholder="Flat no, building, street name"
                    rows={3}
                    className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Landmark">
                    <input
                      type="text"
                      name="landmark"
                      value={checkout.landmark}
                      onChange={handleCheckoutChange}
                      placeholder="Near..."
                      className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                    />
                  </Field>
                  <Field label="Pincode">
                    <input
                      type="text"
                      name="pincode"
                      value={checkout.pincode}
                      onChange={handleCheckoutChange}
                      placeholder="500081"
                      className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                    />
                  </Field>
                </div>
              </>
            ) : (
              <div className="rounded-2xl bg-orange-50 p-4 text-sm text-gray-700">
                Pickup from Cloud Kitchen Express. Ready in about {pickupReadyMinutes} minutes.
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <Field label="Speed">
                <select
                  name="order_type"
                  value={checkout.order_type}
                  onChange={handleCheckoutChange}
                  className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                >
                  <option value="regular">Regular</option>
                  <option value="express">Express</option>
                  <option value="veg">Veg Priority</option>
                </select>
              </Field>
              <Field label="Priority">
                <select
                  name="priority"
                  value={checkout.priority}
                  onChange={handleCheckoutChange}
                  className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-orange-400"
                >
                  <option value="standard">Standard</option>
                  <option value="high">High</option>
                  <option value="urgent">Rush</option>
                </select>
              </Field>
            </div>
          </div>

          {error ? <p className="text-sm font-medium text-red-600">{error}</p> : null}

          <MotionButton
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl bg-gradient-to-r from-orange-500 to-red-500 px-5 py-4 text-sm font-bold text-white shadow-lg hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Placing order..." : "Checkout now"}
          </MotionButton>
        </div>
      </form>
    </motion.aside>
  );
}

export default function OrderForm({ onOrderCreated, onTrackOrder }) {
  const [activeCategory, setActiveCategory] = useState("All");
  const [dietFilter, setDietFilter] = useState("all");
  const [sortBy, setSortBy] = useState("popular");
  const [searchTerm, setSearchTerm] = useState("");
  const [menuItems, setMenuItems] = useState([]);
  const [menuCategories, setMenuCategories] = useState([]);
  const [menuLoading, setMenuLoading] = useState(true);
  const [cart, setCart] = useState({});
  const [checkout, setCheckout] = useState(INITIAL_CHECKOUT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successOrder, setSuccessOrder] = useState(null);
  const [toastMessage, setToastMessage] = useState("");
  const [isPickingLocation, setIsPickingLocation] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [isReverseGeocoding, setIsReverseGeocoding] = useState(false);

  useEffect(() => {
    const fetchMenu = async () => {
      setMenuLoading(true);
      try {
        const res = await fetch(`${API_URL}/menu/`);
        if (!res.ok) throw new Error("Failed to load menu");

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
    if (activeCategory !== "All" && !menuCategories.includes(activeCategory)) {
      setActiveCategory("All");
    }
  }, [activeCategory, menuCategories]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timeout = window.setTimeout(() => setToastMessage(""), 1800);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  const selectedArea = useMemo(() => {
    if (checkout.locality.trim()) return inferDeliveryAreaByLocality(checkout.locality);
    return inferDeliveryAreaByCoords(checkout.user_lat, checkout.user_lng);
  }, [checkout.locality, checkout.user_lat, checkout.user_lng]);

  const visibleMenu = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const filtered = menuItems.filter((item) => {
      const matchesCategory = activeCategory === "All" || item.category === activeCategory;
      const matchesDiet = dietFilter === "all" ? true : dietFilter === "veg" ? item.isVeg : !item.isVeg;
      const matchesSearch =
        !normalizedSearch ||
        item.name.toLowerCase().includes(normalizedSearch) ||
        item.description.toLowerCase().includes(normalizedSearch) ||
        item.category.toLowerCase().includes(normalizedSearch);

      return matchesCategory && matchesDiet && matchesSearch;
    });

    const sorted = [...filtered];
    switch (sortBy) {
      case "price-low":
        sorted.sort((left, right) => left.price - right.price);
        break;
      case "price-high":
        sorted.sort((left, right) => right.price - left.price);
        break;
      case "eta":
        sorted.sort((left, right) => parseInt(left.eta, 10) - parseInt(right.eta, 10));
        break;
      default:
        sorted.sort((left, right) => right.rating - left.rating);
        break;
    }

    return sorted;
  }, [activeCategory, dietFilter, menuItems, searchTerm, sortBy]);

  const cartItems = useMemo(
    () =>
      Object.entries(cart)
        .map(([itemId, quantity]) => {
          const menuItem = menuItems.find((item) => item.id === itemId);
          if (!menuItem || quantity <= 0) return null;

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
    if (successOrder) setSuccessOrder(null);
    setError("");

    setCart((current) => {
      const currentQuantity = current[itemId] || 0;
      if (nextQuantity <= 0) {
        const updated = { ...current };
        delete updated[itemId];
        return updated;
      }

      if (nextQuantity > currentQuantity) {
        const menuItem = menuItems.find((item) => item.id === itemId);
        setToastMessage(`${menuItem?.name || "Item"} added`);
      }

      return { ...current, [itemId]: nextQuantity };
    });
  };

  const handleCheckoutChange = ({ target: { name, value } }) => {
    if (successOrder) setSuccessOrder(null);
    setCheckout((current) => ({ ...current, [name]: value }));
  };

  const handleCartClick = () => {
    const cartPanel = document.getElementById("cart-panel");
    cartPanel?.scrollIntoView({ behavior: "smooth", block: "center" });
    cartPanel?.focus({ preventScroll: true });
  };

  const reverseGeocodeLocation = async ({ lat, lng }) => {
    setIsReverseGeocoding(true);
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&addressdetails=1&zoom=18`,
        { headers: { "Accept-Language": "en" } },
      );
      if (!response.ok) throw new Error("Reverse geocoding request failed");

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

      setCheckout((current) => ({
        ...current,
        locality,
        street_address: streetAddress || current.street_address,
        landmark: address.building || address.amenity || address.shop || address.office || current.landmark,
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
        handleLocationChange({ lat: position.coords.latitude, lng: position.coords.longitude });
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
      if (!res.ok) throw new Error("Failed to create order");

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
    <motion.section
      variants={pageVariants}
      initial="hidden"
      animate="show"
      className="mx-auto max-w-7xl space-y-8 pb-28 lg:pb-0"
    >
      <AnimatePresence>
        {toastMessage ? (
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            className="fixed right-5 top-5 z-50 rounded-2xl bg-gray-900 px-4 py-3 text-sm font-semibold text-white shadow-xl"
          >
            {toastMessage}
          </motion.div>
        ) : null}
      </AnimatePresence>

      <Navbar
        itemCount={itemCount}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        onCartClick={handleCartClick}
      />
      <HeroSection
        featuredImage={menuItems[0]?.image || FALLBACK_MENU_ITEMS[0].image}
        selectedArea={selectedArea}
        isTakeaway={isTakeaway}
        pickupReadyMinutes={pickupReadyMinutes}
      />

      {successOrder ? (
        <motion.section variants={sectionVariants} className="rounded-3xl border border-orange-100 bg-white p-6 shadow-xl">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-orange-500">Order confirmed</p>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900">Order #{successOrder.id.slice(-6)} is live.</h2>
              <p className="mt-2 text-sm text-gray-500">
                {successOrder.fulfillment_mode === "takeaway"
                  ? `Pickup is expected around ${new Date(successOrder.pickup_ready_at).toLocaleString()}.`
                  : `ETA is about ${successOrder.predicted_eta_minutes} minutes for ${successOrder.delivery_area || "your location"}.`}
              </p>
            </div>
            <MotionButton
              type="button"
              onClick={() => onTrackOrder(successOrder.id)}
              className="rounded-full bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600"
            >
              Track order
            </MotionButton>
          </div>
        </motion.section>
      ) : null}

      <CategoryTabs categories={menuCategories} activeCategory={activeCategory} setActiveCategory={setActiveCategory} />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px]">
        <motion.main id="menu-grid" variants={sectionVariants} className="space-y-6">
          <div className="flex flex-col gap-4 rounded-3xl bg-white p-4 shadow-md md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{activeCategory} dishes</h2>
              <p className="text-sm text-gray-500">
                {menuLoading ? "Loading menu..." : `${visibleMenu.length} dishes available now`}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                value={dietFilter}
                onChange={(event) => setDietFilter(event.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:ring-2 focus:ring-orange-400"
              >
                <option value="all">All food</option>
                <option value="veg">Veg only</option>
                <option value="non-veg">Non-veg only</option>
              </select>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:ring-2 focus:ring-orange-400"
              >
                <option value="popular">Popular</option>
                <option value="rating">Rating</option>
                <option value="price-low">Price: Low to High</option>
                <option value="price-high">Price: High to Low</option>
                <option value="eta">Faster delivery</option>
              </select>
            </div>
          </div>

          {menuLoading ? (
            <LoadingSkeleton />
          ) : visibleMenu.length === 0 ? (
            <motion.div variants={sectionVariants} className="rounded-3xl border border-dashed border-gray-300 bg-white px-6 py-14 text-center shadow-md">
              <p className="text-lg font-semibold text-gray-900">No dishes matched</p>
              <p className="mt-2 text-sm text-gray-500">Try another search, cuisine, or food type.</p>
            </motion.div>
          ) : (
            <motion.div layout className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              <AnimatePresence mode="popLayout">
                {visibleMenu.map((item) => (
                  <FoodCard
                    key={item.id}
                    item={item}
                    quantity={cart[item.id] || 0}
                    updateQuantity={updateQuantity}
                  />
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </motion.main>

        <CartPanel
          cartItems={cartItems}
          itemCount={itemCount}
          subtotal={subtotal}
          deliveryFee={deliveryFee}
          platformFee={platformFee}
          taxes={taxes}
          totalAmount={totalAmount}
          checkout={checkout}
          setCheckout={setCheckout}
          handleCheckoutChange={handleCheckoutChange}
          updateQuantity={updateQuantity}
          isTakeaway={isTakeaway}
          pickupReadyMinutes={pickupReadyMinutes}
          isReverseGeocoding={isReverseGeocoding}
          isLocating={isLocating}
          useCurrentLocation={useCurrentLocation}
          isPickingLocation={isPickingLocation}
          setIsPickingLocation={setIsPickingLocation}
          handleLocationChange={handleLocationChange}
          loading={loading}
          error={error}
          handleSubmit={handleSubmit}
        />
      </div>
    </motion.section>
  );
}
