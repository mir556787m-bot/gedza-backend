// frontend/src/api/types.js

/**
 * @typedef {Object} CartPlate
 * @property {number} plateID
 * @property {string} plateName
 * @property {string} thumbnailPicture
 * @property {string} mass
 * @property {number} count
 * @property {number} price
 */

export const CartStatuses = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  COOKING: 'cooking',
  DELIVERING: 'delivering',
  DELIVERED: 'delivered',
  CANCELLED: 'cancelled',
  COMPLETED: 'completed',
};

export const DeliveryTypes = {
  DELIVERY: 'delivery',
  PICKUP: 'pickup',
};