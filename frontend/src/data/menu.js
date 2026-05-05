import butterChickenBowlImage from "../assets/menu/butter-chicken-bowl.jpg";
import coldCoffeeImage from "../assets/menu/cold-coffee.jpg";
import gulabJamunCheesecakeImage from "../assets/menu/gulab-jamun-cheesecake.jpg";
import hyderabadiBiryaniImage from "../assets/menu/hyderabadi-biryani.jpg";
import paneerMakhaniBowlImage from "../assets/menu/paneer-makhani-bowl.jpg";
import paneerTikkaRollImage from "../assets/menu/paneer-tikka-roll.jpg";
import periPeriFriesImage from "../assets/menu/peri-peri-fries.jpg";
import smokyKebabRollImage from "../assets/menu/smoky-kebab-roll.jpg";
import alfredoPastaImage from "../assets/menu/alfredo-pasta.jpg";
import arrabbiataPenneImage from "../assets/menu/arrabbiata-penne.jpg";
import chilliChickenRiceImage from "../assets/menu/chilli-chicken-rice.jpg";
import kimchiRiceBowlImage from "../assets/menu/kimchi-rice-bowl.jpg";
import koreanFriedChickenImage from "../assets/menu/korean-fried-chicken.jpg";
import spicyMisoRamenImage from "../assets/menu/spicy-miso-ramen.jpg";
import vegHakkaNoodlesImage from "../assets/menu/veg-hakka-noodles.jpg";
import vegKoreanRamenImage from "../assets/menu/veg-korean-ramen.jpg";
import mangoLassiImage from "../assets/menu/mango-lassi.png";
import classicMojitoImage from "../assets/menu/classic-mojito.png";
import chocolateLavaCakeImage from "../assets/menu/chocolate-lava-cake.png";
import rasmalaiImage from "../assets/menu/rasmalai.png";
import icedPeachTeaImage from "../assets/menu/iced-peach-tea.png";
import masalaChaiImage from "../assets/menu/masala-chai.png";
import strawberryMilkshakeImage from "../assets/menu/strawberry-milkshake.png";
import chickenTikkaMasalaImage from "../assets/menu/chicken-tikka-masala.png";
import muttonRoganJoshImage from "../assets/menu/mutton-rogan-josh.png";
import garlicNaanImage from "../assets/menu/garlic-naan.png";

export const MENU_IMAGE_MAP = {
  "butter-chicken-bowl": butterChickenBowlImage,
  "hyderabadi-biryani": hyderabadiBiryaniImage,
  "paneer-tikka-roll": paneerTikkaRollImage,
  "smoky-kebab-roll": smokyKebabRollImage,
  "paneer-makhani-bowl": paneerMakhaniBowlImage,
  "peri-peri-fries": periPeriFriesImage,
  "gulab-jamun-cheesecake": gulabJamunCheesecakeImage,
  "alfredo-pasta": alfredoPastaImage,
  "arrabbiata-penne": arrabbiataPenneImage,
  "veg-hakka-noodles": vegHakkaNoodlesImage,
  "chilli-chicken-rice": chilliChickenRiceImage,
  "korean-fried-chicken": koreanFriedChickenImage,
  "kimchi-rice-bowl": kimchiRiceBowlImage,
  "spicy-miso-ramen": spicyMisoRamenImage,
  "veg-korean-ramen": vegKoreanRamenImage,
  "cold-coffee": coldCoffeeImage,
  "mango-lassi": mangoLassiImage,
  "classic-mojito": classicMojitoImage,
  "chocolate-lava-cake": chocolateLavaCakeImage,
  "rasmalai": rasmalaiImage,
  "iced-peach-tea": icedPeachTeaImage,
  "masala-chai": masalaChaiImage,
  "strawberry-milkshake": strawberryMilkshakeImage,
  "chicken-tikka-masala": chickenTikkaMasalaImage,
  "mutton-rogan-josh": muttonRoganJoshImage,
  "garlic-naan": garlicNaanImage,
};

export const FALLBACK_MENU_ITEMS = [
  {
    id: "butter-chicken-bowl",
    name: "Butter Chicken Bowl",
    category: "Bestsellers",
    price: 289,
    rating: 4.7,
    eta: "25-30 mins",
    isVeg: false,
    description: "Creamy tomato gravy with grilled chicken, jeera rice, and onion salad.",
    image: MENU_IMAGE_MAP["butter-chicken-bowl"],
  },
  {
    id: "hyderabadi-biryani",
    name: "Hyderabadi Chicken Biryani",
    category: "Biryani",
    price: 329,
    rating: 4.8,
    eta: "30-35 mins",
    isVeg: false,
    description: "Dum-style biryani layered with saffron rice, masala chicken, and raita.",
    image: MENU_IMAGE_MAP["hyderabadi-biryani"],
  },
  {
    id: "paneer-tikka-roll",
    name: "Paneer Tikka Roll",
    category: "Rolls",
    price: 199,
    rating: 4.5,
    eta: "20-25 mins",
    isVeg: true,
    description: "Charred paneer, mint mayo, pickled onions, and flaky roomali wrap.",
    image: MENU_IMAGE_MAP["paneer-tikka-roll"],
  },
  {
    id: "smoky-kebab-roll",
    name: "Smoky Kebab Roll",
    category: "Rolls",
    price: 229,
    rating: 4.6,
    eta: "20-25 mins",
    isVeg: false,
    description: "Chicken seekh kebab roll with garlic sauce and crunchy onions.",
    image: MENU_IMAGE_MAP["smoky-kebab-roll"],
  },
  {
    id: "paneer-makhani-bowl",
    name: "Paneer Makhani Rice Bowl",
    category: "Bowls",
    price: 249,
    rating: 4.4,
    eta: "25-30 mins",
    isVeg: true,
    description: "Rich makhani paneer with basmati rice and cucumber crunch.",
    image: MENU_IMAGE_MAP["paneer-makhani-bowl"],
  },
  {
    id: "peri-peri-fries",
    name: "Peri Peri Loaded Fries",
    category: "Bestsellers",
    price: 169,
    rating: 4.3,
    eta: "15-20 mins",
    isVeg: true,
    description: "Crispy fries with peri peri dust, cheese drizzle, and spring onions.",
    image: MENU_IMAGE_MAP["peri-peri-fries"],
  },
  {
    id: "gulab-jamun-cheesecake",
    name: "Gulab Jamun Cheesecake",
    category: "Desserts",
    price: 159,
    rating: 4.7,
    eta: "10-15 mins",
    isVeg: true,
    description: "Baked cheesecake topped with warm gulab jamun crumble and syrup glaze.",
    image: MENU_IMAGE_MAP["gulab-jamun-cheesecake"],
  },
  {
    id: "alfredo-pasta",
    name: "Creamy Alfredo Pasta",
    category: "Italian",
    price: 279,
    rating: 4.4,
    eta: "25-30 mins",
    isVeg: true,
    description: "Silky white sauce pasta with herbs, sauteed mushrooms, and garlic toast crumbs.",
    image: MENU_IMAGE_MAP["alfredo-pasta"],
  },
  {
    id: "arrabbiata-penne",
    name: "Arrabbiata Penne",
    category: "Italian",
    price: 259,
    rating: 4.3,
    eta: "25-30 mins",
    isVeg: true,
    description: "Penne tossed in spicy tomato sauce with olives, basil, and parmesan notes.",
    image: MENU_IMAGE_MAP["arrabbiata-penne"],
  },
  {
    id: "veg-hakka-noodles",
    name: "Veg Hakka Noodles",
    category: "Chinese",
    price: 219,
    rating: 4.5,
    eta: "20-25 mins",
    isVeg: true,
    description: "Wok-tossed noodles with crunchy vegetables, soy glaze, and spring onion finish.",
    image: MENU_IMAGE_MAP["veg-hakka-noodles"],
  },
  {
    id: "chilli-chicken-rice",
    name: "Chilli Chicken Rice Bowl",
    category: "Chinese",
    price: 289,
    rating: 4.6,
    eta: "25-30 mins",
    isVeg: false,
    description: "Spicy chilli chicken with fried rice, peppers, and glossy Indo-Chinese sauce.",
    image: MENU_IMAGE_MAP["chilli-chicken-rice"],
  },
  {
    id: "korean-fried-chicken",
    name: "Korean Fried Chicken",
    category: "Korean",
    price: 319,
    rating: 4.7,
    eta: "25-30 mins",
    isVeg: false,
    description: "Crispy fried chicken coated in gochujang glaze with sesame and scallion crunch.",
    image: MENU_IMAGE_MAP["korean-fried-chicken"],
  },
  {
    id: "kimchi-rice-bowl",
    name: "Kimchi Rice Bowl",
    category: "Korean",
    price: 249,
    rating: 4.4,
    eta: "20-25 mins",
    isVeg: true,
    description: "Steamed rice topped with kimchi, sauteed vegetables, sesame, and spicy mayo drizzle.",
    image: MENU_IMAGE_MAP["kimchi-rice-bowl"],
  },
  {
    id: "spicy-miso-ramen",
    name: "Spicy Miso Ramen",
    category: "Ramen",
    price: 329,
    rating: 4.8,
    eta: "30-35 mins",
    isVeg: false,
    description: "Rich miso broth with noodles, chicken slices, egg, corn, and chili oil finish.",
    image: MENU_IMAGE_MAP["spicy-miso-ramen"],
  },
  {
    id: "veg-korean-ramen",
    name: "Veg Korean Ramen",
    category: "Ramen",
    price: 289,
    rating: 4.5,
    eta: "25-30 mins",
    isVeg: true,
    description: "Fiery ramen broth with noodles, tofu, mushrooms, bok choy, and sesame garnish.",
    image: MENU_IMAGE_MAP["veg-korean-ramen"],
  },
  {
    id: "cold-coffee",
    name: "Hazelnut Cold Coffee",
    category: "Beverages",
    price: 129,
    rating: 4.2,
    eta: "10-15 mins",
    isVeg: true,
    description: "Chilled coffee shake with hazelnut notes and whipped cream.",
    image: MENU_IMAGE_MAP["cold-coffee"],
  },
];

export const DELIVERY_AREAS = [
  {
    id: "banjara-hills",
    label: "Banjara Hills",
    address: "Road No. 12, Banjara Hills, Hyderabad",
    user_lat: 17.4126,
    user_lng: 78.4482,
    deliveryFee: 39,
  },
  {
    id: "jubilee-hills",
    label: "Jubilee Hills",
    address: "Road No. 36, Jubilee Hills, Hyderabad",
    user_lat: 17.4326,
    user_lng: 78.4071,
    deliveryFee: 49,
  },
  {
    id: "gachibowli",
    label: "Gachibowli",
    address: "Financial District Road, Gachibowli, Hyderabad",
    user_lat: 17.4401,
    user_lng: 78.3489,
    deliveryFee: 59,
  },
  {
    id: "hitech-city",
    label: "Hitech City",
    address: "Madhapur Main Road, Hitech City, Hyderabad",
    user_lat: 17.4483,
    user_lng: 78.3915,
    deliveryFee: 79,
  },
];
